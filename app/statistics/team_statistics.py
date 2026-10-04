"""Point-in-time team and league statistics.

Every query takes a date ``before`` and uses only matches played strictly before that day. The
match being predicted and every other match on the same day are therefore never included, which
keeps predictions free of data leakage.
"""

from bisect import bisect_left
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.data.models import Match, Outcome
from app.data.preprocessing import sort_chronologically

POINTS_PER_WIN = 3
POINTS_PER_DRAW = 1
DEFAULT_FORM_LENGTH = 5

# Averaged match statistic -> (home side's field, away side's field) in MatchStatistics.
_STATISTIC_FIELDS = {
    "shots": ("home_shots", "away_shots"),
    "shots_on_target": ("home_shots_on_target", "away_shots_on_target"),
    "fouls": ("home_fouls", "away_fouls"),
    "corners": ("home_corners", "away_corners"),
    "yellow_cards": ("home_yellow_cards", "away_yellow_cards"),
    "red_cards": ("home_red_cards", "away_red_cards"),
}


class Venue(StrEnum):
    """Which of a team's matches to include."""

    ALL = "all"
    HOME = "home"
    AWAY = "away"


class TeamResult(StrEnum):
    """A match result from one team's point of view."""

    WIN = "W"
    DRAW = "D"
    LOSS = "L"


@dataclass(frozen=True, slots=True)
class TeamStatistics:
    """A team's record over the selected matches it played before a date."""

    team: str
    before: date
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int

    @property
    def points(self) -> int:
        return POINTS_PER_WIN * self.wins + POINTS_PER_DRAW * self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def points_per_match(self) -> float | None:
        """Points per match, or None when the selection has no matches (as for all rates)."""
        return _per_match(self.points, self.played)

    @property
    def win_rate(self) -> float | None:
        return _per_match(self.wins, self.played)

    @property
    def goals_for_per_match(self) -> float | None:
        return _per_match(self.goals_for, self.played)

    @property
    def goals_against_per_match(self) -> float | None:
        return _per_match(self.goals_against, self.played)


@dataclass(frozen=True, slots=True)
class TeamMatchStatistics:
    """A team's average match statistics per match, its own and its opponents', before a date.

    Only matches with recorded statistics count; every average is None when there are none.
    """

    team: str
    before: date
    matches_with_statistics: int
    shots: float | None
    opponent_shots: float | None
    shots_on_target: float | None
    opponent_shots_on_target: float | None
    fouls: float | None
    opponent_fouls: float | None
    corners: float | None
    opponent_corners: float | None
    yellow_cards: float | None
    opponent_yellow_cards: float | None
    red_cards: float | None
    opponent_red_cards: float | None


@dataclass(frozen=True, slots=True)
class LeagueAverages:
    """League-wide goal averages and outcome frequencies over the selected matches before a date.

    The outcome frequencies are the simplest possible forecast: how often each result happened
    before. Every value is None when the selection has no matches.
    """

    before: date
    matches: int
    home_goals_per_match: float | None
    away_goals_per_match: float | None
    home_win_rate: float | None
    draw_rate: float | None
    away_win_rate: float | None


class MatchHistory:
    """The matches of one competition, indexed chronologically for point-in-time queries.

    The history may also hold matches after a query date; queries never look at them.
    """

    def __init__(self, matches: Iterable[Match]) -> None:
        self._matches = sort_chronologically(matches)
        if not self._matches:
            raise ValueError("a match history needs at least one match")
        competitions = sorted({match.competition for match in self._matches})
        if len(competitions) > 1:
            raise ValueError(
                f"a match history holds one competition, got {', '.join(competitions)}"
            )
        self.competition = competitions[0]
        self._dates = [match.match_date for match in self._matches]
        self._matches_by_team: dict[str, list[Match]] = {}
        for match in self._matches:
            self._matches_by_team.setdefault(match.home_team, []).append(match)
            self._matches_by_team.setdefault(match.away_team, []).append(match)
        self._dates_by_team = {
            team: [match.match_date for match in team_matches]
            for team, team_matches in self._matches_by_team.items()
        }

    @property
    def teams(self) -> list[str]:
        return sorted(self._matches_by_team)

    def matches_before(
        self,
        team: str,
        before: date,
        *,
        season: str | None = None,
        last: int | None = None,
        venue: Venue = Venue.ALL,
    ) -> list[Match]:
        """Return the team's matches played strictly before ``before``, oldest first.

        ``venue`` keeps only home or only away matches, ``season`` keeps one season, and ``last``
        keeps the most recent ``last`` of the remaining matches.
        """
        if team not in self._matches_by_team:
            raise ValueError(f"unknown team {team!r}")
        plays_at_venue: Callable[[Match], bool] | None = {
            Venue.ALL: None,
            Venue.HOME: lambda match: match.home_team == team,
            Venue.AWAY: lambda match: match.away_team == team,
        }[venue]
        return _select_before(
            self._matches_by_team[team],
            self._dates_by_team[team],
            before,
            season=season,
            last=last,
            keep=plays_at_venue,
        )

    def league_matches_before(
        self, before: date, *, season: str | None = None, last: int | None = None
    ) -> list[Match]:
        """Return every match of the competition played strictly before ``before``, oldest first."""
        return _select_before(self._matches, self._dates, before, season=season, last=last)


def team_result(match: Match, team: str) -> TeamResult:
    """Return the result of ``match`` for ``team``, which must have played in it."""
    if team not in (match.home_team, match.away_team):
        raise ValueError(f"{team!r} did not play in {match.home_team} vs {match.away_team}")
    if match.result is Outcome.DRAW:
        return TeamResult.DRAW
    home_won = match.result is Outcome.HOME_WIN
    return TeamResult.WIN if home_won == (team == match.home_team) else TeamResult.LOSS


def team_statistics(
    history: MatchHistory,
    team: str,
    before: date,
    *,
    season: str | None = None,
    last: int | None = None,
    venue: Venue = Venue.ALL,
) -> TeamStatistics:
    """Return the team's record over its selected matches before ``before``.

    The selection options are those of ``MatchHistory.matches_before``.
    """
    matches = history.matches_before(team, before, season=season, last=last, venue=venue)
    results = Counter(team_result(match, team) for match in matches)
    goals_for = sum(m.home_goals if m.home_team == team else m.away_goals for m in matches)
    goals_against = sum(m.away_goals if m.home_team == team else m.home_goals for m in matches)
    return TeamStatistics(
        team=team,
        before=before,
        played=len(matches),
        wins=results[TeamResult.WIN],
        draws=results[TeamResult.DRAW],
        losses=results[TeamResult.LOSS],
        goals_for=goals_for,
        goals_against=goals_against,
    )


def team_match_statistics(
    history: MatchHistory,
    team: str,
    before: date,
    *,
    season: str | None = None,
    last: int | None = None,
    venue: Venue = Venue.ALL,
) -> TeamMatchStatistics:
    """Return the team's average match statistics over its selected matches before ``before``.

    The selection options are those of ``MatchHistory.matches_before``. Matches without recorded
    statistics are left out, so ``last=5`` may average fewer than five matches.
    """
    selected = history.matches_before(team, before, season=season, last=last, venue=venue)
    with_statistics = [match for match in selected if match.statistics is not None]
    averages: dict[str, float | None] = {}
    for name, (home_field, away_field) in _STATISTIC_FIELDS.items():
        own_total = opponent_total = 0
        for match in with_statistics:
            home_value = getattr(match.statistics, home_field)
            away_value = getattr(match.statistics, away_field)
            at_home = match.home_team == team
            own_total += home_value if at_home else away_value
            opponent_total += away_value if at_home else home_value
        averages[name] = _per_match(own_total, len(with_statistics))
        averages[f"opponent_{name}"] = _per_match(opponent_total, len(with_statistics))
    return TeamMatchStatistics(
        team=team,
        before=before,
        matches_with_statistics=len(with_statistics),
        **averages,
    )


def league_averages(
    history: MatchHistory, before: date, *, season: str | None = None, last: int | None = None
) -> LeagueAverages:
    """Return league-wide goal averages and outcome frequencies over matches before ``before``.

    ``season`` keeps one season and ``last`` keeps the most recent ``last`` matches.
    """
    matches = history.league_matches_before(before, season=season, last=last)
    played = len(matches)
    outcomes = Counter(match.result for match in matches)
    return LeagueAverages(
        before=before,
        matches=played,
        home_goals_per_match=_per_match(sum(match.home_goals for match in matches), played),
        away_goals_per_match=_per_match(sum(match.away_goals for match in matches), played),
        home_win_rate=_per_match(outcomes[Outcome.HOME_WIN], played),
        draw_rate=_per_match(outcomes[Outcome.DRAW], played),
        away_win_rate=_per_match(outcomes[Outcome.AWAY_WIN], played),
    )


def recent_form(
    history: MatchHistory,
    team: str,
    before: date,
    *,
    length: int = DEFAULT_FORM_LENGTH,
    season: str | None = None,
    venue: Venue = Venue.ALL,
) -> list[TeamResult]:
    """Return the team's last ``length`` results before ``before``, oldest first."""
    if length < 1:
        raise ValueError(f"length must be at least 1, got {length}")
    matches = history.matches_before(team, before, season=season, last=length, venue=venue)
    return [team_result(match, team) for match in matches]


def _select_before(
    matches: Sequence[Match],
    dates: Sequence[date],
    before: date,
    *,
    season: str | None,
    last: int | None,
    keep: Callable[[Match], bool] | None = None,
) -> list[Match]:
    """Select, from chronologically sorted ``matches``, those played strictly before ``before``.

    A binary search finds the cut-off in O(log n); the scan then walks backwards only as far as
    the selection needs. ``keep`` optionally filters matches (for example by venue).
    """
    if last is not None and last < 1:
        raise ValueError(f"last must be at least 1, got {last}")
    cutoff = bisect_left(dates, before)
    selected: list[Match] = []
    for position in range(cutoff - 1, -1, -1):
        match = matches[position]
        if season is not None and match.season != season:
            if match.season < season:  # labels such as "2006-07" sort chronologically
                break
            continue
        if keep is not None and not keep(match):
            continue
        selected.append(match)
        if last is not None and len(selected) == last:
            break
    selected.reverse()
    return selected


def _per_match(total: int, played: int) -> float | None:
    return total / played if played else None
