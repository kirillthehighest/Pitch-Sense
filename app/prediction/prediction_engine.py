"""The prediction engine: every outcome model for every match, in the shared format.

Each model sees only data from before the day of the match it predicts (see the runners of Elo,
Poisson and logistic regression). A model is missing for a match when it cannot predict it yet:
the Elo draw model and logistic regression need ``min_training_matches`` earlier matches (and
logistic regression all three results), Poisson needs league goals at home and away.

``predict_fixture`` answers a single question (season, home team, away team, date) with the same
code. A match that was not played is added as a placeholder whose score is never used for its own
prediction, because no model looks at results from the day it predicts.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

from app.data.models import Match, Outcome
from app.data.preprocessing import season_date_window, sort_chronologically
from app.prediction.elo_predictions import elo_outcome_predictions, run_elo
from app.prediction.logistic_predictions import MIN_TRAINING_MATCHES, run_logistic_regression
from app.prediction.outputs import (
    ModelName,
    ModelPrediction,
    from_elo,
    from_logistic,
    from_poisson,
)
from app.prediction.poisson_predictions import run_poisson


@dataclass(frozen=True, eq=False)
class MatchPredictions:
    """The predictions available for one match, in the order of ModelName."""

    match: Match
    predictions: Mapping[ModelName, ModelPrediction]

    def of(self, model: ModelName) -> ModelPrediction | None:
        return self.predictions.get(model)

    @property
    def has_all_models(self) -> bool:
        return len(self.predictions) == len(ModelName)


def predict_history(
    matches: Iterable[Match], *, min_training_matches: int = MIN_TRAINING_MATCHES
) -> list[MatchPredictions]:
    """Predict every match of one competition with every model, in chronological order."""
    ordered = sort_chronologically(matches)
    collected: dict[Match, dict[ModelName, ModelPrediction]] = {match: {} for match in ordered}

    elo_run = run_elo(ordered)
    for prediction in elo_outcome_predictions(elo_run, min_matches=min_training_matches):
        collected[prediction.prediction.match][ModelName.ELO] = from_elo(prediction)
    for prediction in run_poisson(ordered):
        collected[prediction.match][ModelName.POISSON] = from_poisson(prediction)
    for prediction in run_logistic_regression(ordered, min_training_matches=min_training_matches):
        collected[prediction.match][ModelName.LOGISTIC_REGRESSION] = from_logistic(prediction)

    return [
        MatchPredictions(
            match=match,
            predictions={
                model: collected[match][model] for model in ModelName if model in collected[match]
            },
        )
        for match in ordered
    ]


@dataclass(frozen=True, eq=False)
class FixturePrediction:
    """Every available model's prediction for one fixture, and the real match if it was played."""

    season: str
    match_date: date
    home_team: str
    away_team: str
    played: Match | None
    predictions: Mapping[ModelName, ModelPrediction]

    def of(self, model: ModelName) -> ModelPrediction | None:
        return self.predictions.get(model)


def predict_fixture(
    matches: Iterable[Match],
    season: str,
    home_team: str,
    away_team: str,
    match_date: date,
    *,
    min_training_matches: int = MIN_TRAINING_MATCHES,
) -> FixturePrediction:
    """Predict one fixture of a season from the data before its date.

    Both teams must have played in ``season`` and the date must fall within the season. When the
    fixture was really played its predictions are exactly those of ``predict_history`` and
    ``played`` holds the real match; otherwise it is predicted as a hypothetical match.
    """
    matches = list(matches)
    season_matches = [match for match in matches if match.season == season]
    if not season_matches:
        raise ValueError(f"no matches in season {season!r}")
    teams = {team for m in season_matches for team in (m.home_team, m.away_team)}
    for team in (home_team, away_team):
        if team not in teams:
            raise ValueError(f"{team!r} did not play in season {season}")
    if home_team == away_team:
        raise ValueError("a team cannot play itself")
    first_day, last_day = season_date_window(season)
    if not first_day <= match_date <= last_day:
        raise ValueError(f"{match_date} is outside season {season}")

    played = next(
        (
            m
            for m in season_matches
            if (m.match_date, m.home_team, m.away_team) == (match_date, home_team, away_team)
        ),
        None,
    )
    relevant = [match for match in matches if match.season <= season]
    target = played
    if target is None:
        target = Match(
            competition=season_matches[0].competition,
            season=season,
            match_date=match_date,
            home_team=home_team,
            away_team=away_team,
            home_goals=0,
            away_goals=0,
            result=Outcome.DRAW,  # placeholder: never used for this fixture's own prediction
        )
        relevant.append(target)
    results = predict_history(relevant, min_training_matches=min_training_matches)
    predictions = next(result for result in results if result.match is target).predictions
    return FixturePrediction(
        season=season,
        match_date=match_date,
        home_team=home_team,
        away_team=away_team,
        played=played,
        predictions=predictions,
    )
