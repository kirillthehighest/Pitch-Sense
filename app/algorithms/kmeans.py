"""K-Means clustering (Lloyd's algorithm with k-means++ starts), implemented with NumPy.

Notation, as in docs/algorithms/kmeans.md:

    n, d, k        numbers of points, features and clusters
    x_i            the i-th point (a standardized feature vector)
    mu_j           the centre (centroid) of cluster j
    D(x, mu)       squared Euclidean distance ||x - mu||^2                                 (Eq. 1)
    c_i            assignment: the cluster j with the smallest D(x_i, mu_j)                 (Eq. 2)
    mu_j           update: the mean of the points assigned to cluster j                     (Eq. 3)
    J              inertia: sum_i D(x_i, mu_{c_i}); no step ever increases it               (Eq. 4)
    k-means++      first centre: a random point; every next centre: a point drawn with      (Eq. 5)
                   probability proportional to its squared distance to the nearest centre
    stop           when no point changes cluster, or after max_iterations                  (Eq. 6)
    empty cluster  its centre moves to the point farthest from its own centre               (Eq. 7)
    s(i)           silhouette: (b_i - a_i) / max(a_i, b_i), where a_i is the mean distance  (Eq. 8)
                   to the other points of its cluster and b_i the mean distance to the
                   nearest other cluster; s(i) = 0 for a point alone in its cluster

The algorithm is run ``restarts`` times from different k-means++ starts and the run with the
lowest inertia is kept. All randomness comes from one seeded generator, so results repeat.
"""

from dataclasses import dataclass

import numpy as np

DEFAULT_RESTARTS = 10
DEFAULT_MAX_ITERATIONS = 300


@dataclass(frozen=True, eq=False)
class FeatureScaling:
    """Per-feature means and standard deviations of the clustered points."""

    means: np.ndarray
    scales: np.ndarray

    @classmethod
    def fit(cls, features: np.ndarray) -> FeatureScaling:
        """Measure the features. A constant feature gets scale 1."""
        features = _as_points(features)
        scales = features.std(axis=0)
        scales[scales == 0] = 1.0
        return cls(means=features.mean(axis=0), scales=scales)

    @classmethod
    def identity(cls, dimensions: int) -> FeatureScaling:
        """Leave the features unchanged."""
        return cls(means=np.zeros(dimensions), scales=np.ones(dimensions))

    def transform(self, features: np.ndarray) -> np.ndarray:
        features = _as_points(features)
        if features.shape[1] != self.means.shape[0]:
            raise ValueError(f"expected {self.means.shape[0]} features, got {features.shape[1]}")
        return (features - self.means) / self.scales

    def inverse(self, points: np.ndarray) -> np.ndarray:
        return points * self.scales + self.means


def squared_distances(points: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    """Eq. 1: the n x k matrix of squared distances from every point to every centre."""
    return ((points[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)


def assign(points: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    """Eq. 2: the index of the nearest centre for every point (ties go to the lower index)."""
    return squared_distances(points, centroids).argmin(axis=1)


def update_centroids(points: np.ndarray, labels: np.ndarray, k: int) -> np.ndarray:
    """Eq. 3 and 7: every centre becomes the mean of its points.

    A cluster without points gets the point farthest from its own (updated) centre; with
    several empty clusters, each takes the next farthest point.
    """
    centroids = np.zeros((k, points.shape[1]))
    sizes = np.bincount(labels, minlength=k)
    for cluster in np.flatnonzero(sizes):
        centroids[cluster] = points[labels == cluster].mean(axis=0)
    empty = np.flatnonzero(sizes == 0)
    if empty.size:
        distance_to_own = ((points - centroids[labels]) ** 2).sum(axis=1)
        for cluster in empty:
            farthest = int(distance_to_own.argmax())
            centroids[cluster] = points[farthest]
            distance_to_own[farthest] = -1.0
    return centroids


def inertia(points: np.ndarray, centroids: np.ndarray, labels: np.ndarray) -> float:
    """Eq. 4: the sum of squared distances from every point to its own centre."""
    return float(((points - centroids[labels]) ** 2).sum())


def kmeans_plus_plus(points: np.ndarray, k: int, generator: np.random.Generator) -> np.ndarray:
    """Eq. 5: choose k starting centres, spread out by distance-weighted sampling."""
    chosen = [int(generator.integers(points.shape[0]))]
    closest = squared_distances(points, points[chosen]).min(axis=1)
    for _ in range(1, k):
        index = int(generator.choice(points.shape[0], p=closest / closest.sum()))
        chosen.append(index)
        closest = np.minimum(closest, squared_distances(points, points[[index]])[:, 0])
    return points[chosen].copy()


def silhouette(points: np.ndarray, labels: np.ndarray) -> float:
    """Eq. 8: the mean silhouette of all points, between -1 and 1 (higher is better)."""
    points = _as_points(points)
    labels = np.asarray(labels)
    clusters = np.unique(labels)
    if not 2 <= clusters.size <= points.shape[0] - 1:
        raise ValueError("the silhouette needs at least 2 clusters and fewer clusters than points")
    distances = np.sqrt(np.maximum(squared_distances(points, points), 0.0))
    sizes = {cluster: int((labels == cluster).sum()) for cluster in clusters}
    mean_distance = {cluster: distances[:, labels == cluster].sum(axis=1) for cluster in clusters}
    scores = np.zeros(points.shape[0])
    for i, own in enumerate(labels):
        if sizes[own] == 1:
            continue
        a = mean_distance[own][i] / (sizes[own] - 1)
        b = min(mean_distance[other][i] / sizes[other] for other in clusters if other != own)
        scores[i] = (b - a) / max(a, b) if max(a, b) > 0 else 0.0
    return float(scores.mean())


@dataclass(frozen=True, eq=False)
class KMeansResult:
    """The best of the runs: centres, assignments and how that run went."""

    centroids: np.ndarray
    labels: np.ndarray
    inertia: float
    inertia_history: tuple[float, ...]
    converged: bool
    scaling: FeatureScaling

    @property
    def iterations(self) -> int:
        return len(self.inertia_history) - 1

    def centroids_in_original_units(self) -> np.ndarray:
        """The centres expressed in the units of the original features."""
        return self.scaling.inverse(self.centroids)

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Assign new points (in original units) to the nearest centre."""
        return assign(self.scaling.transform(features), self.centroids)


def fit(
    features: np.ndarray,
    k: int,
    *,
    restarts: int = DEFAULT_RESTARTS,
    seed: int = 0,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    standardize: bool = True,
    initial_centroids: np.ndarray | None = None,
) -> KMeansResult:
    """Cluster the points into k groups and return the run with the lowest inertia.

    With ``standardize`` every feature is first rescaled to mean 0 and standard deviation 1, so
    that features measured in different units count equally. ``initial_centroids`` (in the same,
    possibly standardized, space) replaces the k-means++ starts with one given start.
    """
    features = _as_points(features)
    if not 1 <= k <= features.shape[0]:
        raise ValueError(f"k must be between 1 and the number of points, got {k}")
    if k > np.unique(features, axis=0).shape[0]:
        raise ValueError(f"k = {k} is larger than the number of distinct points")
    if restarts < 1 or max_iterations < 1:
        raise ValueError("restarts and max_iterations must be at least 1")
    scaling = (
        FeatureScaling.fit(features) if standardize else FeatureScaling.identity(features.shape[1])
    )
    points = scaling.transform(features)

    if initial_centroids is not None:
        if initial_centroids.shape != (k, points.shape[1]):
            raise ValueError(f"initial_centroids must have shape {(k, points.shape[1])}")
        starts = [np.array(initial_centroids, dtype=float)]
    else:
        generator = np.random.default_rng(seed)
        starts = [kmeans_plus_plus(points, k, generator) for _ in range(restarts)]

    best = None
    for start in starts:
        run = _lloyd(points, start, k, max_iterations)
        if best is None or run[2][-1] < best[2][-1]:
            best = run
    centroids, labels, history, converged = best
    centroids.setflags(write=False)
    labels.setflags(write=False)
    return KMeansResult(
        centroids=centroids,
        labels=labels,
        inertia=history[-1],
        inertia_history=tuple(history),
        converged=converged,
        scaling=scaling,
    )


def _lloyd(
    points: np.ndarray, centroids: np.ndarray, k: int, max_iterations: int
) -> tuple[np.ndarray, np.ndarray, list[float], bool]:
    """One run of Lloyd's algorithm (Eq. 2, 3, 6, 7) from the given starting centres."""
    labels = assign(points, centroids)
    history = [inertia(points, centroids, labels)]
    for _ in range(max_iterations):
        centroids = update_centroids(points, labels, k)
        new_labels = assign(points, centroids)
        history.append(inertia(points, centroids, new_labels))
        if np.array_equal(new_labels, labels):
            return centroids, new_labels, history, True
        labels = new_labels
    return centroids, labels, history, False


def _as_points(features: np.ndarray) -> np.ndarray:
    features = np.array(features, dtype=float)
    if features.ndim != 2 or not features.shape[0]:
        raise ValueError("features must be a non-empty two-dimensional n x d matrix")
    if not np.isfinite(features).all():
        raise ValueError("features must be finite numbers")
    return features
