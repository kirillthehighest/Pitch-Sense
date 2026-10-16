"""Predictions for the user interface, with the historical predictions cached.

All real matches, and the matches still to be played of the season in progress, are predicted
once (``prepare``, about 7 s on the full data); afterwards they are answered from the cache. Any
other fixture is predicted on request with ``predict_fixture``. Both paths give identical numbers
for the same match (tested in Phases 7 and 18).

A fixture of the season in progress dated after the last match played is predicted from every
match played so far, whatever its date: nothing newer is known.

The matches screen (Phase 19) reads the cache day by day (``on_day``) and team by team
(``team_matches``); ``season_check`` scores the predictions of a season's matches played so far.

The slow step can run anywhere: ``preparation`` gives it as a job that can be sent to another
process (Phase 21; the server computes in a separate process, so the work never slows it), and
``install`` takes the job's result.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, time, timedelta
from functools import partial

import numpy as np

from app.data.models import Fixture, Match, Outcome
from app.evaluation.metrics import Estimate, accuracy, brier_score, log_loss, outcome_indices
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


@dataclass(frozen=True, eq=False)
class MatchForecast:
    """A match of the calendar, played or scheduled, with every model's prediction for it."""

    competition: str
    season: str
    match_date: date
    kickoff_time: time | None
    home_team: str
    away_team: str
    played: Match | None  # the real match, once played
    predictions: Mapping[ModelName, ModelPrediction]
    as_of: date | None = None  # scheduled: the predictions use the matches before this day
    hypothetical: bool = False  # not in the calendar: two teams and a day chosen by the user

    def of(self, model: ModelName) -> ModelPrediction | None:
        return self.predictions.get(model)

    @property
    def postponed(self) -> bool:
        """Scheduled for a day already past, but without a result yet."""
        return (
            self.played is None
            and not self.hypothetical
            and self.as_of is not None
            and self.match_date < self.as_of
        )


def forecast_of(prediction: FixturePrediction, competition: str) -> MatchForecast:
    """A prediction asked for on request, as the matches screen shows it."""
    return MatchForecast(
        competition=competition,
        season=prediction.season,
        match_date=prediction.match_date,
        kickoff_time=prediction.played.kickoff_time if prediction.played else None,
        home_team=prediction.home_team,
        away_team=prediction.away_team,
        played=prediction.played,
        predictions=prediction.predictions,
        as_of=prediction.as_of,
        hypothetical=prediction.played is None,
    )


@dataclass(frozen=True, slots=True)
class ModelCheck:
    """How one model's predictions of a season's matches played so far turned out."""

    model: ModelName
    accuracy: Estimate
    brier_score: Estimate
    log_loss: Estimate


@dataclass(frozen=True, eq=False)
class SeasonCheck:
    """The models scored on the matches of one season predicted by all of them."""

    season: str
    matches: int
    first_day: date | None
    last_day: date | None
    models: tuple[ModelCheck, ...]


# A played match is a surprise for a model when the result that happened had less than this
# chance in its prediction (an upset: the model thought it would happen less than once in five).
SURPRISE_CHANCE = 0.2


@dataclass(frozen=True, eq=False)
class ReviewedMatch:
    """A played match as one model saw it before kickoff."""

    forecast: MatchForecast
    chance: float  # the probability the model gave the result that happened
    hit: bool  # the model's most likely outcome happened
    surprise: bool  # the result had less than SURPRISE_CHANCE


@dataclass(frozen=True, eq=False)
class SeasonReview:
    """One model's predictions of a season's played matches, against what happened."""

    season: str
    model: ModelName
    matches: tuple[ReviewedMatch, ...]  # in the order they were played

    @property
    def hits(self) -> int:
        return sum(match.hit for match in self.matches)

    @property
    def surprises(self) -> int:
        return sum(match.surprise for match in self.matches)

    def by_result(self) -> dict[Outcome, tuple[int, int]]:
        """For each result that happened: (matches the model got right, matches)."""
        counts = {outcome: (0, 0) for outcome in Outcome}
        for match in self.matches:
            hits, total = counts[match.forecast.played.result]
            counts[match.forecast.played.result] = (hits + match.hit, total + 1)
        return counts


@dataclass(frozen=True, slots=True)
class PreparedPredictions:
    """The result of the slow step: every real match's predictions and every fixture's."""

    results: tuple[MatchPredictions, ...]
    upcoming: tuple[UpcomingPrediction, ...]


def compute_predictions(
    matches: Sequence[Match], fixtures: Sequence[Fixture], min_training_matches: int
) -> PreparedPredictions:
    """Predict every real match and every fixture (about 7 s for a league's 20 seasons)."""
    if fixtures:
        results, upcoming = predict_season(
            matches, fixtures, min_training_matches=min_training_matches
        )
        return PreparedPredictions(tuple(results), tuple(upcoming))
    results = predict_history(matches, min_training_matches=min_training_matches)
    return PreparedPredictions(tuple(results), ())


def featured_match(
    forecasts: Sequence[MatchForecast],
    strength: Callable[[MatchForecast], float],
    favourite: str | None = None,
) -> MatchForecast | None:
    """The match of the day among ``forecasts`` (one league's matches of one day): the favourite
    team's, else the one whose teams are strongest by ``strength`` (the sum of their ratings, for
    instance); None without matches. Ties go to the earliest."""
    if favourite is not None:
        for forecast in forecasts:
            if favourite in (forecast.home_team, forecast.away_team):
                return forecast
    return max(forecasts, key=strength) if forecasts else None


def _forecast_order(forecast: MatchForecast) -> tuple[date, time, str]:
    return forecast.match_date, forecast.kickoff_time or time.min, forecast.home_team


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
        self._days: dict[date, list[MatchForecast]] = {}
        self._current_season = self._fixtures[0].season if self._fixtures else None
        last_played = max(match.match_date for match in self._matches)
        self._as_of = last_played + timedelta(days=1)  # nothing newer is known

    @property
    def is_prepared(self) -> bool:
        return self._history is not None

    def prepare(self) -> None:
        """Predict every real match and every fixture once (the slow step); later calls do
        nothing."""
        if self._history is None:
            self.install(self.preparation()())

    def preparation(self) -> Callable[[], PreparedPredictions]:
        """The slow step as a job that can run in another process (its arguments are plain
        data, and it calls a module-level function)."""
        return partial(
            compute_predictions, self._matches, self._fixtures, self._min_training_matches
        )

    def install(self, prepared: PreparedPredictions) -> None:
        """Answer from ``prepared`` from now on (a second result is ignored)."""
        if self._history is not None:
            return
        self._upcoming = {
            (prediction.fixture.home_team, prediction.fixture.away_team): prediction
            for prediction in prepared.upcoming
        }
        history = {result.match: result for result in prepared.results}
        days: dict[date, list[MatchForecast]] = defaultdict(list)
        for match, result in history.items():
            days[match.match_date].append(self._played_forecast(match, result.predictions))
        for upcoming in self._upcoming.values():
            fixture = upcoming.fixture
            days[fixture.match_date].append(
                MatchForecast(
                    competition=fixture.competition,
                    season=fixture.season,
                    match_date=fixture.match_date,
                    kickoff_time=fixture.kickoff_time,
                    home_team=fixture.home_team,
                    away_team=fixture.away_team,
                    played=None,
                    predictions=upcoming.predictions,
                    as_of=upcoming.as_of,
                )
            )
        self._days = {day: sorted(found, key=_forecast_order) for day, found in days.items()}
        self._history = history

    def match_days(self) -> list[date]:
        """Every day with a match, played or scheduled, in order."""
        self.prepare()
        return sorted(self._days)

    def nearest_match_day(self, day: date) -> date | None:
        """``day`` when it has matches, else the league's next day with matches, else its last
        one; None without matches at all."""
        days = self.match_days()
        later = [found for found in days if found >= day]
        if later:
            return later[0]
        return days[-1] if days else None

    def on_day(self, day: date) -> list[MatchForecast]:
        """The matches of one day, by kickoff time, then home team; empty without matches."""
        self.prepare()
        return list(self._days.get(day, ()))

    def team_matches(self, team: str, season: str) -> list[MatchForecast]:
        """A team's matches of one season, played and scheduled, in order."""
        self.prepare()
        return sorted(
            (
                forecast
                for forecasts in self._days.values()
                for forecast in forecasts
                if forecast.season == season and team in (forecast.home_team, forecast.away_team)
            ),
            key=_forecast_order,
        )

    def review(self, season: str, model: ModelName) -> SeasonReview:
        """How ``model``'s predictions of the season's played matches turned out; matches the
        model could not predict (too few earlier matches) are left out."""
        self.prepare()
        reviewed = []
        for match in self._matches:
            if match.season != season:
                continue
            predictions = self._history[match].predictions
            prediction = predictions.get(model)
            if prediction is None:
                continue
            probabilities = prediction.probabilities
            chance = probabilities.of(match.result)
            reviewed.append(
                ReviewedMatch(
                    forecast=self._played_forecast(match, predictions),
                    chance=chance,
                    hit=probabilities.most_likely == match.result,
                    surprise=chance < SURPRISE_CHANCE,
                )
            )
        reviewed.sort(key=lambda match: _forecast_order(match.forecast))
        return SeasonReview(season, model, tuple(reviewed))

    def season_check(self, season: str) -> SeasonCheck:
        """Score every model on the season's played matches that all of them predicted."""
        self.prepare()
        scored = [
            (match, self._history[match].predictions)
            for match in self._matches
            if match.season == season and len(self._history[match].predictions) == len(ModelName)
        ]
        if not scored:
            return SeasonCheck(season, 0, None, None, ())
        actual = outcome_indices([match.result.value for match, _ in scored])
        checks = []
        for model in ModelName:
            probabilities = np.array(
                [predictions[model].probabilities.as_tuple() for _, predictions in scored]
            )
            checks.append(
                ModelCheck(
                    model=model,
                    accuracy=accuracy(probabilities, actual),
                    brier_score=brier_score(probabilities, actual),
                    log_loss=log_loss(probabilities, actual),
                )
            )
        days = [match.match_date for match, _ in scored]
        return SeasonCheck(season, len(scored), min(days), max(days), tuple(checks))

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

    @staticmethod
    def _played_forecast(
        match: Match, predictions: Mapping[ModelName, ModelPrediction]
    ) -> MatchForecast:
        return MatchForecast(
            competition=match.competition,
            season=match.season,
            match_date=match.match_date,
            kickoff_time=match.kickoff_time,
            home_team=match.home_team,
            away_team=match.away_team,
            played=match,
            predictions=predictions,
        )

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
