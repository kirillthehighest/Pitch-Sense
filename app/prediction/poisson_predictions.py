"""Run the Poisson model through historical matches, using only statistics from before each day."""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.algorithms.poisson import (
    DEFAULT_MAX_GOALS,
    ScoreDistribution,
    expected_goals,
    recency_weights,
    score_distribution,
    strength,
)
from app.data.models import Match
from app.data.preprocessing import sort_chronologically
from app.prediction.settings import PoissonSettings, settings_of
from app.statistics.team_statistics import MatchHistory, Venue, league_averages


@dataclass(frozen=True, slots=True)
class WeightedRecord:
    """A team's goals for and against over its selected matches, each weighted (Eq. 7)."""

    goals_for: float
    goals_against: float
    matches: float  # the sum of the weights


def weighted_record(
    history: MatchHistory,
    team: str,
    before: date,
    *,
    last: int,
    venue: Venue,
    half_life: float | None,
) -> WeightedRecord:
    """The team's last ``last`` matches at ``venue`` before ``before``, the most recent weighing
    the most (equal weights without ``half_life``)."""
    matches = history.matches_before(team, before, last=last, venue=venue)
    weights = recency_weights(len(matches), half_life)
    goals_for = goals_against = 0.0
    for match, weight in zip(matches, weights, strict=True):
        at_home = match.home_team == team
        goals_for += weight * (match.home_goals if at_home else match.away_goals)
        goals_against += weight * (match.away_goals if at_home else match.home_goals)
    return WeightedRecord(goals_for, goals_against, math.fsum(weights))


@dataclass(frozen=True, eq=False)
class PoissonPrediction:
    """The Poisson view of one match, computed only from matches before the match's day."""

    match: Match
    league_home_goals: float
    league_away_goals: float
    home_attack: float
    home_defence_weakness: float
    away_attack: float
    away_defence_weakness: float
    distribution: ScoreDistribution


def predict_match(
    history: MatchHistory,
    match: Match,
    settings: PoissonSettings,
    *,
    max_goals: int = DEFAULT_MAX_GOALS,
) -> PoissonPrediction | None:
    """Predict one match from the matches before its day (Eq. 4 and 5 of the Poisson model).

    The home team's strengths come from its last ``team_window`` home matches, the away team's
    from its last ``team_window`` away matches, weighted by recency when the settings give a
    half-life (Eq. 7), and the league averages from the last ``league_window`` matches. The
    score table gets the settings' Dixon-Coles rho (Eq. 6). Returns None while the league
    history has no home or no away goals yet (the competition's first days).
    """
    _check_settings(settings)
    team_window, prior_matches, league_window = (
        settings.team_window,
        settings.prior_matches,
        settings.league_window,
    )
    before = match.match_date
    league = league_averages(history, before, last=league_window)
    home_average, away_average = league.home_goals_per_match, league.away_goals_per_match
    if not home_average or not away_average:
        return None
    home = weighted_record(
        history,
        match.home_team,
        before,
        last=team_window,
        venue=Venue.HOME,
        half_life=settings.half_life,
    )
    away = weighted_record(
        history,
        match.away_team,
        before,
        last=team_window,
        venue=Venue.AWAY,
        half_life=settings.half_life,
    )

    home_attack = strength(home.goals_for, home.matches, home_average, prior_matches)
    home_defence_weakness = strength(home.goals_against, home.matches, away_average, prior_matches)
    away_attack = strength(away.goals_for, away.matches, away_average, prior_matches)
    away_defence_weakness = strength(away.goals_against, away.matches, home_average, prior_matches)
    distribution = score_distribution(
        expected_goals(home_attack, away_defence_weakness, home_average),
        expected_goals(away_attack, home_defence_weakness, away_average),
        max_goals,
        settings.rho,
    )
    return PoissonPrediction(
        match=match,
        league_home_goals=home_average,
        league_away_goals=away_average,
        home_attack=home_attack,
        home_defence_weakness=home_defence_weakness,
        away_attack=away_attack,
        away_defence_weakness=away_defence_weakness,
        distribution=distribution,
    )


def run_poisson(
    matches: Iterable[Match],
    settings: PoissonSettings | None = None,
    *,
    max_goals: int = DEFAULT_MAX_GOALS,
) -> list[PoissonPrediction]:
    """Predict every match of one competition, in chronological order.

    Matches without enough league history (see ``predict_match``) get no prediction. Without
    ``settings`` the competition's calibrated N, m, league window, half-life and rho are used.
    """
    ordered = sort_chronologically(matches)
    if not ordered:
        return []
    settings = settings or settings_of(ordered).poisson
    _check_settings(settings)
    history = MatchHistory(ordered)
    predictions = []
    for match in ordered:
        prediction = predict_match(history, match, settings, max_goals=max_goals)
        if prediction is not None:
            predictions.append(prediction)
    return predictions


def _check_settings(settings: PoissonSettings) -> None:
    team_window, prior_matches, league_window = (
        settings.team_window,
        settings.prior_matches,
        settings.league_window,
    )
    if settings.half_life is not None and not (
        math.isfinite(settings.half_life) and settings.half_life > 0
    ):
        raise ValueError(f"half_life must be a positive number or None, got {settings.half_life}")
    if not math.isfinite(settings.rho):
        raise ValueError(f"rho must be a finite number, got {settings.rho}")
    if team_window < 1 or league_window < 1:
        raise ValueError(f"windows must be at least 1, got {team_window} and {league_window}")
    if not prior_matches > 0:
        raise ValueError(
            f"prior_matches must be positive so that teams without history get a strength, "
            f"got {prior_matches}"
        )
