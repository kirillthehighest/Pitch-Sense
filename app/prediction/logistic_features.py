"""Features for logistic regression, built for every match from data before its day.

Each feature is a difference "home team minus away team", so a positive value favours the home
side. A team without the needed history gets the league average at that moment instead, taken
separately for home and away teams so that the home advantage is kept.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.data.models import Match, Outcome
from app.data.preprocessing import sort_chronologically
from app.prediction.elo_predictions import run_elo
from app.prediction.poisson_predictions import LEAGUE_WINDOW
from app.statistics.team_statistics import (
    DEFAULT_FORM_LENGTH,
    MatchHistory,
    Venue,
    team_match_statistics,
    team_statistics,
)

FEATURE_NAMES = (
    "elo_difference",
    "points_per_match_difference",
    "goal_difference_per_match_difference",
    "form_difference",
    "shots_on_target_difference",
)
VENUE_WINDOW = 19  # one season of home (or away) matches in a 20-team league


@dataclass(frozen=True, slots=True)
class MatchFeatures:
    """The feature values of one match, in the order of FEATURE_NAMES."""

    match: Match
    values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class _LeagueReference:
    """League averages before a date, used for teams without the needed history."""

    home_points_per_match: float
    away_points_per_match: float
    points_per_match: float
    home_goal_difference: float
    home_shots_on_target_difference: float

    @classmethod
    def from_matches(cls, matches: Sequence[Match]) -> _LeagueReference:
        played = len(matches)
        home_wins = sum(match.result is Outcome.HOME_WIN for match in matches) / played
        draws = sum(match.result is Outcome.DRAW for match in matches) / played
        away_wins = 1.0 - home_wins - draws
        goal_difference = sum(m.home_goals - m.away_goals for m in matches) / played
        with_statistics = [m.statistics for m in matches if m.statistics is not None]
        shots_difference = (
            sum(s.home_shots_on_target - s.away_shots_on_target for s in with_statistics)
            / len(with_statistics)
            if with_statistics
            else 0.0
        )
        return cls(
            home_points_per_match=3 * home_wins + draws,
            away_points_per_match=3 * away_wins + draws,
            points_per_match=(3 - draws) / 2,
            home_goal_difference=goal_difference,
            home_shots_on_target_difference=shots_difference,
        )


def build_features(matches: Iterable[Match]) -> list[MatchFeatures]:
    """Return the features of every match of one competition, in chronological order.

    Matches on the competition's first day have no earlier league matches and are left out.
    """
    ordered = sort_chronologically(matches)
    history = MatchHistory(ordered)
    elo_differences = {
        _key(p.match): p.home_rating - p.away_rating for p in run_elo(ordered).predictions
    }
    features = []
    for match in ordered:
        league_matches = history.league_matches_before(match.match_date, last=LEAGUE_WINDOW)
        if not league_matches:
            continue
        league = _LeagueReference.from_matches(league_matches)
        home = _team_values(history, match, match.home_team, Venue.HOME, league)
        away = _team_values(history, match, match.away_team, Venue.AWAY, league)
        values = (elo_differences[_key(match)], *(h - a for h, a in zip(home, away, strict=True)))
        features.append(MatchFeatures(match=match, values=values))
    return features


def _team_values(
    history: MatchHistory, match: Match, team: str, venue: Venue, league: _LeagueReference
) -> tuple[float, float, float, float]:
    """Points per match and goal difference per match at the venue, form, shots on target."""
    at_home = venue is Venue.HOME
    sign = 1 if at_home else -1
    before = match.match_date
    record = team_statistics(history, team, before, last=VENUE_WINDOW, venue=venue)
    form = team_statistics(history, team, before, last=DEFAULT_FORM_LENGTH)
    shots = team_match_statistics(history, team, before, last=VENUE_WINDOW, venue=venue)

    points = record.points_per_match
    if points is None:
        points = league.home_points_per_match if at_home else league.away_points_per_match
    if record.played:
        goal_difference = record.goal_difference / record.played
    else:
        goal_difference = sign * league.home_goal_difference
    recent_points = form.points_per_match
    if recent_points is None:
        recent_points = league.points_per_match
    if shots.shots_on_target is None or shots.opponent_shots_on_target is None:
        shots_difference = sign * league.home_shots_on_target_difference
    else:
        shots_difference = shots.shots_on_target - shots.opponent_shots_on_target
    return points, goal_difference, recent_points, shots_difference


def _key(match: Match) -> tuple:
    return match.match_date, match.home_team, match.away_team
