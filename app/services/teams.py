"""Team analysis for the user interface: a team's record, form and profile, and league tables.

Everything is computed "as of" a date from the matches before it. Without a date, the whole
season is used (for the season in progress: every match played so far). The league table orders
teams by points, then goal difference, then goals scored; La Liga breaks ties by head-to-head
results first, which is not modelled here. The season in progress is never profiled or grouped by
K-Means, because a profile describes a completed season.
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
from app.prediction.elo_predictions import EloRun, run_elo
from app.statistics.team_profiles import (
    PROFILE_FEATURES,
    TeamSeasonProfile,
    has_shot_statistics,
    profiled_seasons,
    season_profiles,
    seasons_in,
)
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

# Names of the k = 4 groups shown to the user (Romanian), from the clusters of all seasons
# (docs/algorithms/kmeans.md).
GROUP_NAMES = {
    0: "Elită",
    1: "Jumătatea de sus",
    2: "Jumătatea de jos, puternică acasă",
    3: "Slabă peste tot",
}
PROMOTED_NAME = "Promovată (fără sezonul anterior în ligă)"
NO_STATISTICS_NAME = "Indisponibil (sezonul nu are statistici de șuturi)"
FIRST_SEASON_NAME = "Indisponibil (primul sezon din date)"
_GOALS_SCORED = PROFILE_FEATURES.index("goals_scored_per_match")
_GOALS_CONCEDED = PROFILE_FEATURES.index("goals_conceded_per_match")


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
    in_progress: bool = False  # the season is still being played


@dataclass(frozen=True, slots=True)
class RatingSeason:
    """A team's Elo rating going into each of its matches of one season."""

    season: str
    dates: tuple[date, ...]
    ratings: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class GroupPoint:
    """A team's whole-season goals per match and its descriptive K-Means group."""

    team: str
    goals_scored: float
    goals_conceded: float
    group: int


@dataclass(frozen=True, slots=True)
class GroupCentre:
    """The goals per match of a group's centre, fitted on the profiles of all seasons."""

    group: int
    goals_scored: float
    goals_conceded: float


@dataclass(frozen=True, slots=True)
class SeasonGroups:
    """The descriptive groups of one season's teams, with the group centres.

    The groups come from all six profile values; the goals per match are two of them.
    """

    season: str
    teams: tuple[GroupPoint, ...]
    centres: tuple[GroupCentre, ...]  # ordered by group


class TeamService:
    """Team statistics, league tables and profiles for one competition."""

    def __init__(self, matches: Iterable[Match], *, in_progress: str | None = None) -> None:
        self._history = MatchHistory(matches)
        self._seasons = seasons_in(self._history)
        if in_progress is not None and in_progress != self._seasons[-1]:
            raise ValueError(f"the season in progress must be the latest, not {in_progress}")
        self.in_progress = in_progress
        self._clusters: ProfileClusters | None = None
        self._groups: dict[str, dict[str, int | None]] = {}
        self._elo: EloRun | None = None

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
        finished = before >= end and season != self.in_progress
        profile = None
        season_group = None
        if finished and not has_shot_statistics(self._history, season):
            season_group = NO_STATISTICS_NAME
        elif finished:
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
            in_progress=season == self.in_progress,
        )

    def elo_history(self, team: str) -> tuple[RatingSeason, ...]:
        """The team's rating before each of its matches, season by season, oldest first.

        These are the ratings the Elo predictions used: each comes from earlier days only.
        """
        if self._elo is None:
            self._elo = run_elo(self._history.league_matches_before(date.max))
        seasons: dict[str, tuple[list[date], list[float]]] = {}
        for prediction in self._elo.predictions:
            match = prediction.match
            if team not in (match.home_team, match.away_team):
                continue
            rating = prediction.home_rating if team == match.home_team else prediction.away_rating
            dates, ratings = seasons.setdefault(match.season, ([], []))
            dates.append(match.match_date)
            ratings.append(rating)
        if not seasons:
            raise ValueError(f"{team!r} played no matches")
        return tuple(
            RatingSeason(season=season, dates=tuple(dates), ratings=tuple(ratings))
            for season, (dates, ratings) in seasons.items()
        )

    def season_groups(self, season: str) -> SeasonGroups:
        """Every team of a season placed in its descriptive group, as in ``overview``."""
        self._season_matches(season)  # an unknown season is an error
        if season == self.in_progress:
            raise ValueError(f"season {season} is in progress, so its teams have no groups yet")
        if not has_shot_statistics(self._history, season):
            raise ValueError(f"season {season} has no shot statistics, so its teams have no groups")
        clusters = self._descriptive()
        profiles = [profile for profile in clusters.profiles if profile.season == season]
        centres = clusters.result.centroids_in_original_units()
        return SeasonGroups(
            season=season,
            teams=tuple(
                GroupPoint(
                    team=profile.team,
                    goals_scored=profile.values[_GOALS_SCORED],
                    goals_conceded=profile.values[_GOALS_CONCEDED],
                    group=clusters.group_of(profile),
                )
                for profile in profiles
            ),
            centres=tuple(
                sorted(
                    (
                        GroupCentre(
                            group=group,
                            goals_scored=float(centre[_GOALS_SCORED]),
                            goals_conceded=float(centre[_GOALS_CONCEDED]),
                        )
                        for centre, group in zip(centres, clusters.group_of_cluster, strict=True)
                    ),
                    key=lambda centre: centre.group,
                )
            ),
        )

    def _pre_season_group(self, season: str, team: str) -> str:
        if season == self._seasons[0]:
            return FIRST_SEASON_NAME
        previous = self._seasons[self._seasons.index(season) - 1]
        if not has_shot_statistics(self._history, previous):
            return NO_STATISTICS_NAME
        if season not in self._groups:
            self._groups[season] = point_in_time_groups(self._history, season, CLUSTER_COUNT)
        group = self._groups[season][team]
        return PROMOTED_NAME if group is None else GROUP_NAMES[group]

    def _descriptive(self) -> ProfileClusters:
        if self._clusters is None:
            seasons = [s for s in profiled_seasons(self._history) if s != self.in_progress]
            self._clusters = descriptive_clusters(self._history, seasons, CLUSTER_COUNT)
        return self._clusters

    def _season_matches(self, season: str) -> list[Match]:
        matches = self._history.league_matches_before(date.max, season=season)
        if not matches:
            raise ValueError(f"no matches in season {season!r}")
        return matches
