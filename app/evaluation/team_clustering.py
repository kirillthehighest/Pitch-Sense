"""Team profile clusters: K-Means applied to season profiles, in two ways.

1. Descriptive: cluster the profiles of completed seasons, to describe what kinds of teams exist.
   These clusters use whole seasons and are never inputs for predictions.
2. Point in time: for a season S, fit the clusters only on seasons before S and place every team
   by its profile in season S - 1. Teams that were not in the league in S - 1 (promoted) get no
   cluster. These groups are known before S starts, so they may be used to break down the
   evaluation of predictions made during S.

Cluster numbers from K-Means are arbitrary and change between fits, so clusters are reported as
groups ranked by the points per match of their centre: group 0 is the strongest.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np

from app.algorithms.kmeans import KMeansResult, fit
from app.statistics.team_profiles import (
    PROFILE_FEATURES,
    TeamSeasonProfile,
    has_shot_statistics,
    season_profiles,
    seasons_in,
)
from app.statistics.team_statistics import MatchHistory

# Chosen by the team with `python -m app.evaluation.kmeans_selection` on the profiles of
# 2006/07-2009/10; see docs/algorithms/kmeans.md.
CLUSTER_COUNT = 4
_POINTS = PROFILE_FEATURES.index("points_per_match")


@dataclass(frozen=True, eq=False)
class ProfileClusters:
    """K-Means fitted on a set of team-season profiles."""

    profiles: tuple[TeamSeasonProfile, ...]
    result: KMeansResult

    @property
    def k(self) -> int:
        return self.result.centroids.shape[0]

    def cluster_of(self, profile: TeamSeasonProfile) -> int:
        """The nearest cluster for any profile, also one that was not used for fitting."""
        return int(self.result.predict(np.array([profile.values]))[0])

    @property
    def group_of_cluster(self) -> tuple[int, ...]:
        """For every cluster, its group: its rank by the centre's points per match (0 = best)."""
        points = self.result.centroids_in_original_units()[:, _POINTS]
        ranks = np.empty(self.k, dtype=int)
        ranks[np.argsort(-points, kind="stable")] = np.arange(self.k)
        return tuple(int(rank) for rank in ranks)

    def group_of(self, profile: TeamSeasonProfile) -> int:
        """The group of any profile: the rank of its nearest cluster (0 = strongest)."""
        return self.group_of_cluster[self.cluster_of(profile)]

    @property
    def groups(self) -> tuple[int, ...]:
        """The group of every fitted profile, in the order of ``profiles``."""
        return tuple(self.group_of_cluster[label] for label in self.result.labels)


def cluster_profiles(
    profiles: Sequence[TeamSeasonProfile], k: int = CLUSTER_COUNT, seed: int = 0
) -> ProfileClusters:
    """Fit K-Means (standardized features, k-means++ starts) on the given profiles."""
    if not profiles:
        raise ValueError("need at least one profile")
    result = fit(np.array([profile.values for profile in profiles]), k, seed=seed)
    return ProfileClusters(profiles=tuple(profiles), result=result)


def descriptive_clusters(
    history: MatchHistory, seasons: Sequence[str], k: int = CLUSTER_COUNT, seed: int = 0
) -> ProfileClusters:
    """Cluster the profiles of every team in the given completed seasons (descriptive only)."""
    profiles = [profile for season in seasons for profile in season_profiles(history, season)]
    return cluster_profiles(profiles, k, seed)


def point_in_time_groups(
    history: MatchHistory, season: str, k: int = CLUSTER_COUNT, seed: int = 0
) -> dict[str, int | None]:
    """Return the group of every team of ``season``, using only seasons before it.

    The clusters are fitted on all seasons before ``season`` that have shot statistics; each
    team is placed by its profile in the season just before, and reported as its group
    (0 = strongest). Teams without such a profile get None: promoted teams, or every team when
    the season before has no statistics (Ligue 1 2006/07).
    """
    all_seasons = seasons_in(history)
    if season not in all_seasons:
        raise ValueError(f"no matches in season {season!r}")
    earlier = [label for label in all_seasons if label < season]
    if not earlier:
        raise ValueError(f"there is no completed season before {season}")
    season_matches = history.league_matches_before(date.max, season=season)
    # The clubs taking part in a season are known before it starts.
    teams = sorted({team for m in season_matches for team in (m.home_team, m.away_team)})
    profiled = [label for label in earlier if has_shot_statistics(history, label)]
    if earlier[-1] not in profiled:
        return dict.fromkeys(teams)
    clusters = descriptive_clusters(history, profiled, k, seed)
    previous = {profile.team: profile for profile in season_profiles(history, earlier[-1])}
    return {team: clusters.group_of(previous[team]) if team in previous else None for team in teams}
