"""Run Elo through historical matches, predicting each day before learning its results."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import groupby

from app.algorithms.elo import (
    DEFAULT_DRAW_BINS,
    DEFAULT_PRIOR_WEIGHT,
    DrawModel,
    EloRatings,
    GameResult,
    actual_score,
)
from app.data.models import Match
from app.data.preprocessing import sort_chronologically
from app.prediction.schedule import week_start
from app.prediction.settings import EloSettings, settings_for

MIN_DRAW_MODEL_MATCHES = 100


@dataclass(frozen=True, slots=True)
class EloPrediction:
    """The Elo view of one match, computed from the ratings before the match's day."""

    match: Match
    home_rating: float
    away_rating: float
    expected_home_score: float


@dataclass(frozen=True, slots=True)
class EloRun:
    """Every match's prediction, in chronological order, and the ratings after the last match."""

    predictions: tuple[EloPrediction, ...]
    final_ratings: Mapping[str, float]


def run_elo(matches: Iterable[Match], settings: EloSettings | None = None) -> EloRun:
    """Walk through the matches of one competition day by day.

    When a season starts, the league's teams are set; the clubs taking part in a season are known
    before it begins. Every match of a day is predicted from the ratings before that day, and
    only then are the day's results applied, so no prediction uses a result from its own day.
    Without ``settings`` the competition's calibrated K, H and goal-margin choice are used.
    """
    ordered = sort_chronologically(matches)
    if not ordered:
        raise ValueError("need at least one match")
    competitions = sorted({match.competition for match in ordered})
    if len(competitions) > 1:
        raise ValueError(f"Elo rates one competition at a time, got {', '.join(competitions)}")
    settings = settings or settings_for(competitions[0]).elo
    teams_by_season: dict[str, set[str]] = {}
    for match in ordered:
        teams_by_season.setdefault(match.season, set()).update((match.home_team, match.away_team))

    elo = EloRatings(
        k_factor=settings.k_factor,
        home_advantage=settings.home_advantage,
        goal_margin=settings.goal_margin,
    )
    predictions: list[EloPrediction] = []
    current_season = None
    for match_date, day in groupby(ordered, key=lambda match: match.match_date):
        day_matches = list(day)
        seasons = {match.season for match in day_matches}
        if len(seasons) > 1:
            raise ValueError(f"matches on {match_date} belong to several seasons")
        season = seasons.pop()
        if season != current_season:
            elo.start_season(teams_by_season[season])
            current_season = season
        for match in day_matches:
            predictions.append(
                EloPrediction(
                    match=match,
                    home_rating=elo.rating(match.home_team),
                    away_rating=elo.rating(match.away_team),
                    expected_home_score=elo.expected_home_score(match.home_team, match.away_team),
                )
            )
        for match in day_matches:
            elo.update(
                GameResult(
                    match.match_date,
                    match.home_team,
                    match.away_team,
                    match.home_goals,
                    match.away_goals,
                )
            )
    return EloRun(predictions=tuple(predictions), final_ratings=elo.ratings)


@dataclass(frozen=True, slots=True)
class EloOutcomePrediction:
    """Elo's home/draw/away probabilities for one match (Eq. 4-6 of the Elo module)."""

    prediction: EloPrediction
    probabilities: tuple[float, float, float]  # home win, draw, away win
    draw_model_matches: int


def elo_outcome_predictions(
    run: EloRun,
    *,
    min_matches: int = MIN_DRAW_MODEL_MATCHES,
    bins: int = DEFAULT_DRAW_BINS,
    prior_weight: float = DEFAULT_PRIOR_WEIGHT,
) -> list[EloOutcomePrediction]:
    """Turn the expected scores of a run into home/draw/away probabilities.

    Every Monday the draw model is refitted on the expected and actual scores of all matches
    played before that Monday; it then converts the expected scores of that week's matches.
    Weeks starting with fewer than ``min_matches`` earlier matches get no probabilities.
    """
    if min_matches < 1:
        raise ValueError(f"min_matches must be at least 1, got {min_matches}")
    expected_scores: list[float] = []
    actual_scores: list[float] = []
    outcome_predictions = []
    for _, week in groupby(run.predictions, key=lambda p: week_start(p.match.match_date)):
        week_predictions = list(week)
        if len(expected_scores) >= min_matches:
            draw_model = DrawModel.fit(expected_scores, actual_scores, bins, prior_weight)
            outcome_predictions.extend(
                EloOutcomePrediction(
                    prediction=prediction,
                    probabilities=draw_model.outcome_probabilities(prediction.expected_home_score),
                    draw_model_matches=len(expected_scores),
                )
                for prediction in week_predictions
            )
        for prediction in week_predictions:
            expected_scores.append(prediction.expected_home_score)
            match = prediction.match
            actual_scores.append(actual_score(match.home_goals, match.away_goals))
    return outcome_predictions
