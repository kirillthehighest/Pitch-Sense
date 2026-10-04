"""Compare numbers of clusters k for the team profiles and describe the chosen clusters.

Run from the project folder with ``python -m app.evaluation.kmeans_selection``.

k is chosen on the profiles of the warm-up and calibration seasons only, because hyperparameters
are never tuned on the reported period. For every k the command prints the inertia, its drop from
k - 1, the mean silhouette and the stability: the mean Rand index between the clusterings found
from 10 different seeds. The same comparison on all seasons follows as a descriptive reference,
and finally the chosen groups, described in the original units with their most typical teams.
"""

import itertools
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.algorithms.kmeans import fit, silhouette
from app.data.paths import DATABASE_PATH
from app.data.repository import MatchRepository
from app.evaluation.periods import CALIBRATION_SEASONS, WARM_UP_SEASONS
from app.evaluation.team_clustering import CLUSTER_COUNT, ProfileClusters, cluster_profiles
from app.statistics.team_profiles import TeamSeasonProfile, season_profiles, seasons_in
from app.statistics.team_statistics import MatchHistory

COMPETITION = "SP1"
K_VALUES = tuple(range(2, 9))
SEEDS = tuple(range(10))


@dataclass(frozen=True, slots=True)
class KComparison:
    """How well the profiles split into k clusters."""

    k: int
    inertia: float
    silhouette: float
    stability: float
    smallest_cluster: int


@dataclass(frozen=True, slots=True)
class GroupSummary:
    """One group: its size, its centre in original units and its most typical team-seasons."""

    group: int
    size: int
    centre: tuple[float, ...]
    examples: tuple[str, ...]


def rand_index(first: Sequence[int], second: Sequence[int]) -> float:
    """The share of point pairs on which two clusterings agree (same cluster or not).

    1 means identical groupings, whatever numbers the clusters carry.
    """
    first, second = np.asarray(first), np.asarray(second)
    if first.shape != second.shape or first.size < 2:
        raise ValueError("need two labellings of the same, at least two, points")
    same_in_first = first[:, None] == first[None, :]
    same_in_second = second[:, None] == second[None, :]
    pairs = np.triu_indices(first.size, k=1)
    return float((same_in_first == same_in_second)[pairs].mean())


def compare_k(
    profiles: Sequence[TeamSeasonProfile],
    k_values: Sequence[int] = K_VALUES,
    seeds: Sequence[int] = SEEDS,
) -> list[KComparison]:
    """Compare every k, skipping values larger than the number of distinct profiles."""
    features = np.array([profile.values for profile in profiles])
    distinct = np.unique(features, axis=0).shape[0]
    comparisons = []
    for k in k_values:
        if not 2 <= k <= distinct:
            continue
        runs = [fit(features, k, seed=seed) for seed in seeds]
        best = runs[0]
        stability = (
            np.mean([rand_index(a.labels, b.labels) for a, b in itertools.combinations(runs, 2)])
            if len(runs) > 1
            else 1.0
        )
        comparisons.append(
            KComparison(
                k=k,
                inertia=best.inertia,
                silhouette=silhouette(best.scaling.transform(features), best.labels),
                stability=float(stability),
                smallest_cluster=int(np.bincount(best.labels).min()),
            )
        )
    return comparisons


def summarize(clusters: ProfileClusters, examples: int = 3) -> list[GroupSummary]:
    """Describe every group, strongest first, with the profiles closest to its centre."""
    features = np.array([profile.values for profile in clusters.profiles])
    standardized = clusters.result.scaling.transform(features)
    centres = clusters.result.centroids_in_original_units()
    summaries = []
    for cluster, group in sorted(enumerate(clusters.group_of_cluster), key=lambda pair: pair[1]):
        members = np.flatnonzero(clusters.result.labels == cluster)
        distances = ((standardized[members] - clusters.result.centroids[cluster]) ** 2).sum(axis=1)
        typical = members[np.argsort(distances, kind="stable")[:examples]]
        summaries.append(
            GroupSummary(
                group=group,
                size=int(members.size),
                centre=tuple(float(value) for value in centres[cluster]),
                examples=tuple(
                    f"{clusters.profiles[i].team} {clusters.profiles[i].season}" for i in typical
                ),
            )
        )
    return summaries


def main(database_path: Path = DATABASE_PATH, competition: str = COMPETITION) -> int:
    """Print the comparisons and the chosen groups. Returns the process exit code."""
    if not database_path.is_file():
        print(
            f"Database not found: {database_path}\nRun: python -m app.data.build_database",
            file=sys.stderr,
        )
        return 1
    with MatchRepository.open(database_path) as repository:
        history = MatchHistory(repository.matches(competition))
    available = seasons_in(history)
    choosing = [
        season for season in (*WARM_UP_SEASONS, *CALIBRATION_SEASONS) if season in available
    ]
    for title, seasons in (
        (f"Choosing k on {', '.join(choosing)}", choosing),
        ("Reference, all seasons (descriptive, not used for choosing)", available),
    ):
        profiles = [profile for season in seasons for profile in season_profiles(history, season)]
        print(f"{title}: {len(profiles)} team-season profiles")
        print("  k   inertia   drop   silhouette   stability   smallest")
        previous = None
        for row in compare_k(profiles):
            drop = "" if previous is None else f"{(previous - row.inertia) / previous:.1%}"
            print(
                f"{row.k:3d}  {row.inertia:8.1f}  {drop:>6}   {row.silhouette:8.3f}"
                f"     {row.stability:7.3f}   {row.smallest_cluster:6d}"
            )
            previous = row.inertia
    all_profiles = [profile for season in available for profile in season_profiles(history, season)]
    print(f"\nChosen k = {CLUSTER_COUNT}, groups on all seasons (strongest first):")
    print("group  goals  conceded  on-target  on-target-against  points  home-away  size  examples")
    for summary in summarize(cluster_profiles(all_profiles)):
        values = "  ".join(f"{value:6.2f}" for value in summary.centre)
        print(f"{summary.group:5d}  {values}  {summary.size:4d}  {', '.join(summary.examples)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
