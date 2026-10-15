"""Predictions for the user interface, with the historical predictions cached.

All real matches, and the matches still to be played of the season in progress, are predicted
once (``prepare``, about 7 s on the full data); afterwards they are answered from the cache. Any
other fixture is predicted on request with ``predict_fixture``. Both paths give identical numbers
for the same match (tested in Phases 7 and 18).

A fixture of the season in progress dated after the last match played is predicted from every
match played so far, whatever its date: nothing newer is known.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta

import numpy as np

from app.data.models import Fixture, Match, Outcome
from app.prediction.logistic_predictions import MIN_TRAINING_MATCHES
from app.prediction.outputs import ModelName, ModelPrediction
from app.prediction.prediction_engine import (
    FixturePrediction,
    MatchPredictions,
    UpcomingPrediction,
    predict_fixture,
    predict_history,
    predict_season,
)

TOP_SCORES = 5


@dataclass(frozen=True, eq=False)
class ModelSummary:
    """One model's prediction, ready to display."""

    model: ModelName
    home_win: float
    draw: float
    away_win: float
    most_likely: Outcome
    expected_goals: tuple[float, float] | None
    top_scores: tuple[tuple[int, int, float], ...]  # (home goals, away goals, probability)
    score_probabilities: np.ndarray | None  # [home goals, away goals], read-only


def summarize(prediction: ModelPrediction, top_scores: int = TOP_SCORES) -> ModelSummary:
    """Turn a model prediction into display values; only Poisson has goals and scores."""
    probabilities = prediction.probabilities
    scores: tuple[tuple[int, int, float], ...] = ()
    distribution = prediction.score_distribution
    if distribution is not None:
        scores = tuple(distribution.most_likely_scores(top_scores))
    return ModelSummary(
        model=prediction.model,
        home_win=probabilities.home_win,
        draw=probabilities.draw,
        away_win=probabilities.away_win,
        most_likely=probabilities.most_likely,
        expected_goals=prediction.expected_goals,
        top_scores=scores,
        score_probabilities=None if distribution is None else distribution.probabilities,
    )


class PredictionService:
    """Predictions for one competition's matches and, when given, its fixtures still to play."""

    def __init__(
        self,
        matches: Iterable[Match],
        fixtures: Sequence[Fixture] = (),
        *,
        min_training_matches: int = MIN_TRAINING_MATCHES,
    ) -> None:
        self._matches = list(matches)
        self._fixtures = tuple(fixtures)
        self._min_training_matches = min_training_matches
        self._history: dict[Match, MatchPredictions] | None = None
        self._upcoming: dict[tuple[str, str], UpcomingPrediction] | None = None
        self._current_season = self._fixtures[0].season if self._fixtures else None
        last_played = max(match.match_date for match in self._matches)
        self._as_of = last_played + timedelta(days=1)  # nothing newer is known

    @property
    def is_prepared(self) -> bool:
        return self._history is not None

    def prepare(self) -> None:
        """Predict every real match and every fixture once (the slow step); later calls do
        nothing."""
        if self._history is not None:
            return
        if self._fixtures:
            results, upcoming = predict_season(
                self._matches, self._fixtures, min_training_matches=self._min_training_matches
            )
            self._upcoming = {
                (prediction.fixture.home_team, prediction.fixture.away_team): prediction
                for prediction in upcoming
            }
        else:
            results = predict_history(
                self._matches, min_training_matches=self._min_training_matches
            )
            self._upcoming = {}
        self._history = {result.match: result for result in results}

    def upcoming(self) -> list[UpcomingPrediction]:
        """The predictions of the fixtures still to be played, in chronological order."""
        self.prepare()
        return list(self._upcoming.values())

    def predict(
        self, season: str, home_team: str, away_team: str, match_date: date
    ) -> FixturePrediction:
        """Predict a fixture: from the cache when it was played or is scheduled, otherwise on
        request."""
        played = self._played(season, home_team, away_team, match_date)
        if played is not None and self._history is not None:
            return FixturePrediction(
                season=season,
                match_date=match_date,
                home_team=home_team,
                away_team=away_team,
                played=played,
                predictions=self._history[played].predictions,
            )
        knowledge_day = match_date
        if season == self._current_season and played is None:
            scheduled = self._scheduled(home_team, away_team)
            if match_date >= self._as_of or (
                scheduled is not None and scheduled.match_date == match_date
            ):
                knowledge_day = self._as_of
            if knowledge_day == self._as_of and self._upcoming:
                cached = self._upcoming.get((home_team, away_team))
                if cached is not None:
                    return FixturePrediction(
                        season=season,
                        match_date=match_date,
                        home_team=home_team,
                        away_team=away_team,
                        played=None,
                        predictions=cached.predictions,
                        as_of=cached.as_of,
                    )
        prediction = predict_fixture(
            self._matches,
            season,
            home_team,
            away_team,
            knowledge_day,
            min_training_matches=self._min_training_matches,
        )
        return replace(prediction, match_date=match_date)

    def _scheduled(self, home_team: str, away_team: str) -> Fixture | None:
        return next(
            (f for f in self._fixtures if (f.home_team, f.away_team) == (home_team, away_team)),
            None,
        )

    def _played(
        self, season: str, home_team: str, away_team: str, match_date: date
    ) -> Match | None:
        for match in self._matches:
            if (match.season, match.match_date, match.home_team, match.away_team) == (
                season,
                match_date,
                home_team,
                away_team,
            ):
                return match
        return None
