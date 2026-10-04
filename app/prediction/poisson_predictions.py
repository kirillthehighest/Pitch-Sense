"""Run the Poisson model through historical matches, using only statistics from before each day."""

from collections.abc import Iterable
from dataclasses import dataclass

from app.algorithms.poisson import (
    DEFAULT_MAX_GOALS,
    ScoreDistribution,
    expected_goals,
    score_distribution,
    strength,
)
from app.data.models import Match
from app.data.preprocessing import sort_chronologically
from app.statistics.team_statistics import MatchHistory, Venue, league_averages, team_statistics

LEAGUE_WINDOW = 380  # league averages over the last 380 matches: one season of a 20-team league
# Chosen by `python -m app.evaluation.poisson_calibration` on the calibration seasons
# 2007/08-2009/10 (mean -ln P(actual score) 2.95326); see docs/algorithms/poisson.md.
TEAM_WINDOW = 38
PRIOR_MATCHES = 20.0


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
    *,
    team_window: int = TEAM_WINDOW,
    prior_matches: float = PRIOR_MATCHES,
    league_window: int = LEAGUE_WINDOW,
    max_goals: int = DEFAULT_MAX_GOALS,
) -> PoissonPrediction | None:
    """Predict one match from the matches before its day (Eq. 4 and 5 of the Poisson model).

    The home team's strengths come from its last ``team_window`` home matches, the away team's
    from its last ``team_window`` away matches, and the league averages from the last
    ``league_window`` matches. Returns None while the league history has no home or no away
    goals yet (the competition's first days).
    """
    _check_settings(team_window, prior_matches, league_window)
    before = match.match_date
    league = league_averages(history, before, last=league_window)
    home_average, away_average = league.home_goals_per_match, league.away_goals_per_match
    if not home_average or not away_average:
        return None
    home = team_statistics(history, match.home_team, before, last=team_window, venue=Venue.HOME)
    away = team_statistics(history, match.away_team, before, last=team_window, venue=Venue.AWAY)

    home_attack = strength(home.goals_for, home.played, home_average, prior_matches)
    home_defence_weakness = strength(home.goals_against, home.played, away_average, prior_matches)
    away_attack = strength(away.goals_for, away.played, away_average, prior_matches)
    away_defence_weakness = strength(away.goals_against, away.played, home_average, prior_matches)
    distribution = score_distribution(
        expected_goals(home_attack, away_defence_weakness, home_average),
        expected_goals(away_attack, home_defence_weakness, away_average),
        max_goals,
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
    *,
    team_window: int = TEAM_WINDOW,
    prior_matches: float = PRIOR_MATCHES,
    league_window: int = LEAGUE_WINDOW,
    max_goals: int = DEFAULT_MAX_GOALS,
) -> list[PoissonPrediction]:
    """Predict every match of one competition, in chronological order.

    Matches without enough league history (see ``predict_match``) get no prediction.
    """
    _check_settings(team_window, prior_matches, league_window)
    ordered = sort_chronologically(matches)
    history = MatchHistory(ordered)
    predictions = []
    for match in ordered:
        prediction = predict_match(
            history,
            match,
            team_window=team_window,
            prior_matches=prior_matches,
            league_window=league_window,
            max_goals=max_goals,
        )
        if prediction is not None:
            predictions.append(prediction)
    return predictions


def _check_settings(team_window: int, prior_matches: float, league_window: int) -> None:
    if team_window < 1 or league_window < 1:
        raise ValueError(f"windows must be at least 1, got {team_window} and {league_window}")
    if not prior_matches > 0:
        raise ValueError(
            f"prior_matches must be positive so that teams without history get a strength, "
            f"got {prior_matches}"
        )
