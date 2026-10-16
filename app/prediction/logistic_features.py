"""Features for logistic regression, built for every match from data before its day.

Each of the five base features is a difference "home team minus away team", so a positive value
favours the home side. A team without the needed history gets the league average at that moment
instead, taken separately for home and away teams so that the home advantage is kept.

Two more features (Phase 23) are added when a league's calibration chooses them:

- ``elo_gap``, |Elo difference|: how close the teams are, whichever is stronger. The five base
  features are linear in "home minus away", so the draw, most likely between close teams, could
  only respond to a side's advantage; the gap lets it rise as the teams get closer.
- ``expected_goals_difference``, the Poisson model's lambda_home - lambda_away for the match,
  from matches before its day; before the Poisson model can predict, the league's home minus
  away goals per match.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.data.models import Match, Outcome
from app.data.preprocessing import sort_chronologically
from app.prediction.elo_predictions import run_elo
from app.prediction.poisson_predictions import PoissonPrediction, run_poisson
from app.prediction.settings import LogisticSettings, settings_of
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
ELO_GAP = "elo_gap"
EXPECTED_GOALS_DIFFERENCE = "expected_goals_difference"
EXTRA_FEATURES = (ELO_GAP, EXPECTED_GOALS_DIFFERENCE)


def feature_names(settings: LogisticSettings) -> tuple[str, ...]:
    """The names of the features ``build_features`` gives with these settings, in order."""
    unknown = sorted(set(settings.extra_features) - set(EXTRA_FEATURES))
    if unknown:
        raise ValueError(f"unknown logistic regression features: {', '.join(unknown)}")
    if EXPECTED_GOALS_DIFFERENCE in settings.extra_features and settings.poisson is None:
        raise ValueError("the expected-goals difference needs the Poisson settings")
    return (*FEATURE_NAMES, *(name for name in EXTRA_FEATURES if name in settings.extra_features))


@dataclass(frozen=True, slots=True)
class MatchFeatures:
    """The feature values of one match, in the order of ``feature_names`` of its settings."""

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


def build_features(
    matches: Iterable[Match],
    settings: LogisticSettings | None = None,
    *,
    poisson: Sequence[PoissonPrediction] | None = None,
) -> list[MatchFeatures]:
    """Return the features of every match of one competition, in chronological order.

    Matches on the competition's first day have no earlier league matches and are left out.
    Without ``settings`` the competition's calibrated Elo, windows and features are used.
    ``poisson`` may give the Poisson predictions of the same matches with ``settings.poisson``,
    already computed, for the expected-goals difference.
    """
    ordered = sort_chronologically(matches)
    settings = settings or settings_of(ordered).logistic
    extras = feature_names(settings)[len(FEATURE_NAMES) :]
    history = MatchHistory(ordered)
    elo_differences = {
        _key(p.match): p.home_rating - p.away_rating
        for p in run_elo(ordered, settings.elo).predictions
    }
    expected_differences = {}
    if EXPECTED_GOALS_DIFFERENCE in extras:
        expected_differences = {
            _key(p.match): p.distribution.home_expected_goals - p.distribution.away_expected_goals
            for p in (run_poisson(ordered, settings.poisson) if poisson is None else poisson)
        }
    features = []
    for match in ordered:
        league_matches = history.league_matches_before(
            match.match_date, last=settings.league_window
        )
        if not league_matches:
            continue
        league = _LeagueReference.from_matches(league_matches)
        window = settings.venue_window
        home = _team_values(history, match, match.home_team, Venue.HOME, league, window)
        away = _team_values(history, match, match.away_team, Venue.AWAY, league, window)
        elo_difference = elo_differences[_key(match)]
        values = (elo_difference, *(h - a for h, a in zip(home, away, strict=True)))
        if ELO_GAP in extras:
            values += (abs(elo_difference),)
        if EXPECTED_GOALS_DIFFERENCE in extras:
            values += (expected_differences.get(_key(match), league.home_goal_difference),)
        features.append(MatchFeatures(match=match, values=values))
    return features


def _team_values(
    history: MatchHistory,
    match: Match,
    team: str,
    venue: Venue,
    league: _LeagueReference,
    venue_window: int,
) -> tuple[float, float, float, float]:
    """Points per match and goal difference per match at the venue, form, shots on target."""
    at_home = venue is Venue.HOME
    sign = 1 if at_home else -1
    before = match.match_date
    record = team_statistics(history, team, before, last=venue_window, venue=venue)
    form = team_statistics(history, team, before, last=DEFAULT_FORM_LENGTH)
    shots = team_match_statistics(history, team, before, last=venue_window, venue=venue)

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
