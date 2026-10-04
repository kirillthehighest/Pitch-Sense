"""Team analysis for the user interface: a team's record, form and profile, and league tables.

Everything is computed "as of" a date from the matches before it. Without a date, the whole
season is used. The league table orders teams by points, then goal difference, then goals
scored; La Liga breaks ties by head-to-head results first, which is not modelled here.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from app.data.models import Match
from app.evaluation.team_clustering import (
    CLUSTER_COUNT,
    ProfileClusters,
    descriptive_clusters,
    point_in_time_groups,
)
from app.statistics.team_profiles import TeamSeasonProfile, season_profiles, seasons_in
from app.statistics.team_statistics import (
    MatchHistory,
    TeamMatchStatistics,
    TeamResult,
    TeamStatistics,
    Venue,
    recent_form,
    team_match_statistics,
    team_statistics,
)

# Names of the k = 4 groups, from the clusters of all seasons (docs/algorithms/kmeans.md).
GROUP_NAMES = {
    0: "Elite",
    1: "Upper half",
    2: "Lower half, strong at home",
    3: "Weak everywhere",
}
PROMOTED_NAME = "Promoted (no previous season)"


@dataclass(frozen=True, slots=True)
class StandingRow:
    """One line of a league table."""

    position: int
    team: str
    record: TeamStatistics


@dataclass(frozen=True, eq=False)
class TeamOverview:
    """A team's season up to a date, with its K-Means groups."""

    team: str
    season: str
    before: date
    record: TeamStatistics
    home: TeamStatistics
    away: TeamStatistics
    form: tuple[TeamResult, ...]
    match_statistics: TeamMatchStatistics
    position: int
    pre_season_group: str  # point-in-time group from the previous season (Phase 6, use 2)
    season_profile: TeamSeasonProfile | None  # whole-season profile, only for a finished season
    season_group: str | None  # descriptive group of that whole-season profile


class TeamService:
    """Team statistics, league tables and profiles for one competition."""

    def __init__(self, matches: Iterable[Match]) -> None:
        self._history = MatchHistory(matches)
        self._seasons = seasons_in(self._history)
        self._clusters: ProfileClusters | None = None
        self._groups: dict[str, dict[str, int | None]] = {}

    def season_end(self, season: str) -> date:
        """The day after the season's last match: queries on it see the whole season."""
        matches = self._season_matches(season)
        return matches[-1].match_date + timedelta(days=1)

    def standings(self, season: str, before: date | None = None) -> list[StandingRow]:
        """The league table of ``season`` from the matches before ``before`` (default: all)."""
        before = before or self.season_end(season)
        teams = sorted(
            {t for m in self._season_matches(season) for t in (m.home_team, m.away_team)}
        )
        records = [team_statistics(self._history, team, before, season=season) for team in teams]
        records.sort(key=lambda r: (-r.points, -r.goal_difference, -r.goals_for, r.team))
        return [
            StandingRow(position=index + 1, team=record.team, record=record)
            for index, record in enumerate(records)
        ]

    def overview(self, season: str, team: str, before: date | None = None) -> TeamOverview:
        """The team's season up to ``before`` (default: the whole season)."""
        end = self.season_end(season)
        before = before or end
        if team not in {row.team for row in self.standings(season, end)}:
            raise ValueError(f"{team!r} did not play in season {season}")
        position = next(row.position for row in self.standings(season, before) if row.team == team)
        finished = before >= end
        profile = None
        season_group = None
        if finished:
            profile = next(p for p in season_profiles(self._history, season) if p.team == team)
            season_group = GROUP_NAMES[self._descriptive().group_of(profile)]
        return TeamOverview(
            team=team,
            season=season,
            before=before,
            record=team_statistics(self._history, team, before, season=season),
            home=team_statistics(self._history, team, before, season=season, venue=Venue.HOME),
            away=team_statistics(self._history, team, before, season=season, venue=Venue.AWAY),
            form=tuple(recent_form(self._history, team, before)),
            match_statistics=team_match_statistics(self._history, team, before, season=season),
            position=position,
            pre_season_group=self._pre_season_group(season, team),
            season_profile=profile,
            season_group=season_group,
        )

    def _pre_season_group(self, season: str, team: str) -> str:
        if season == self._seasons[0]:
            return "Not available (first season of the data)"
        if season not in self._groups:
            self._groups[season] = point_in_time_groups(self._history, season, CLUSTER_COUNT)
        group = self._groups[season][team]
        return PROMOTED_NAME if group is None else GROUP_NAMES[group]

    def _descriptive(self) -> ProfileClusters:
        if self._clusters is None:
            self._clusters = descriptive_clusters(self._history, self._seasons, CLUSTER_COUNT)
        return self._clusters

    def _season_matches(self, season: str) -> list[Match]:
        matches = self._history.league_matches_before(date.max, season=season)
        if not matches:
            raise ValueError(f"no matches in season {season!r}")
        return matches
