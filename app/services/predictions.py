"""Predictions for the user interface, with the historical predictions cached.

All real matches are predicted once (``prepare``, about 7 s on the full data); afterwards any
real match is answered from the cache. A fixture that was not played is predicted on request with
``predict_fixture``. Both paths give identical numbers for a real match (tested in Phase 7).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import numpy as np

from app.data.models import Match, Outcome
from app.prediction.logistic_predictions import MIN_TRAINING_MATCHES
from app.prediction.outputs import ModelName, ModelPrediction
from app.prediction.prediction_engine import (
    FixturePrediction,
    MatchPredictions,
    predict_fixture,
    predict_history,
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
    """Predictions for one competition's matches."""

    def __init__(
        self, matches: Iterable[Match], *, min_training_matches: int = MIN_TRAINING_MATCHES
    ) -> None:
        self._matches = list(matches)
        self._min_training_matches = min_training_matches
        self._history: dict[Match, MatchPredictions] | None = None

    @property
    def is_prepared(self) -> bool:
        return self._history is not None

    def prepare(self) -> None:
        """Predict every real match once (the slow step); later calls do nothing."""
        if self._history is None:
            results = predict_history(
                self._matches, min_training_matches=self._min_training_matches
            )
            self._history = {result.match: result for result in results}

    def predict(
        self, season: str, home_team: str, away_team: str, match_date: date
    ) -> FixturePrediction:
        """Predict a fixture: from the cache when it was played, otherwise on request."""
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
        return predict_fixture(
            self._matches,
            season,
            home_team,
            away_team,
            match_date,
            min_training_matches=self._min_training_matches,
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
