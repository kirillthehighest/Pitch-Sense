import math

import numpy as np
import pytest

from app.algorithms.kmeans import (
    FeatureScaling,
    assign,
    fit,
    inertia,
    kmeans_plus_plus,
    silhouette,
    squared_distances,
    update_centroids,
)

LINE = np.array([[0.0], [1.0], [10.0], [11.0]])
TRUE_CENTRES = np.array([[0.0, 0.0], [8.0, 1.0], [3.0, 9.0]])


def blobs(per_cluster: int = 50, seed: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """Three well-separated groups of points around TRUE_CENTRES, and their true groups."""
    generator = np.random.default_rng(seed)
    points = np.vstack(
        [centre + 0.5 * generator.standard_normal((per_cluster, 2)) for centre in TRUE_CENTRES]
    )
    return points, np.repeat(np.arange(3), per_cluster)


def same_grouping(first: np.ndarray, second: np.ndarray) -> bool:
    """True when two labellings split the points identically, whatever the cluster numbers."""
    pairs = set(zip(first.tolist(), second.tolist(), strict=True))
    return len(pairs) == len(set(first.tolist())) == len(set(second.tolist()))


# --- Eq. 1-4 ---


def test_squared_distances_and_assignment():
    centroids = np.array([[0.5], [10.5]])

    np.testing.assert_allclose(squared_distances(LINE, centroids)[0], [0.25, 110.25])
    assert assign(LINE, centroids).tolist() == [0, 0, 1, 1]


def test_update_moves_each_centre_to_the_mean_of_its_points():
    centroids = update_centroids(LINE, np.array([0, 0, 1, 1]), k=2)

    np.testing.assert_allclose(centroids, [[0.5], [10.5]])
    assert inertia(LINE, centroids, np.array([0, 0, 1, 1])) == pytest.approx(4 * 0.25)


def test_an_empty_cluster_moves_to_the_farthest_point():
    points = np.array([[0.0], [1.0], [10.0]])

    # Everything is in cluster 0 (mean 11/3); the farthest point from it is 10.
    centroids = update_centroids(points, np.array([0, 0, 0]), k=2)

    np.testing.assert_allclose(centroids, [[11 / 3], [10.0]])


def test_several_empty_clusters_take_different_points():
    points = np.array([[0.0], [1.0], [10.0], [-9.0]])

    centroids = update_centroids(points, np.array([0, 0, 0, 0]), k=3)

    assert sorted(centroids[1:, 0].tolist()) == [-9.0, 10.0]


# --- Eq. 5: k-means++ ---


def test_kmeans_plus_plus_picks_distinct_points_even_with_duplicates():
    points = np.array([[0.0], [0.0], [0.0], [5.0], [9.0]])

    centres = kmeans_plus_plus(points, 3, np.random.default_rng(1))

    assert sorted(centres[:, 0].tolist()) == [0.0, 5.0, 9.0]


# --- full algorithm ---


def test_hand_example_without_standardization():
    points = np.array([[0.0, 0.0], [0.0, 1.0], [10.0, 10.0], [10.0, 11.0]])

    result = fit(points, k=2, standardize=False)

    assert same_grouping(result.labels, np.array([0, 0, 1, 1]))
    assert sorted(result.centroids.tolist()) == [[0.0, 0.5], [10.0, 10.5]]
    assert result.inertia == pytest.approx(1.0)
    assert result.converged


def test_inertia_never_increases():
    points, _ = blobs()

    # A deliberately poor start: both outer centres near one group.
    result = fit(
        points, k=3, initial_centroids=np.array([[-1.0, -1.0], [-0.9, -1.0], [-1.0, -0.9]])
    )

    history = np.array(result.inertia_history)
    assert (np.diff(history) <= 1e-9).all()
    assert history[-1] < history[0]


def test_well_separated_groups_are_recovered():
    points, true_groups = blobs()

    result = fit(points, k=3, seed=7)

    assert same_grouping(result.labels, true_groups)
    found = sorted(result.centroids_in_original_units().round(0).tolist())
    assert found == sorted(TRUE_CENTRES.tolist())


def test_one_cluster_is_the_mean_of_everything():
    points, _ = blobs()

    result = fit(points, k=1)

    np.testing.assert_allclose(result.centroids_in_original_units()[0], points.mean(axis=0))
    standardized = FeatureScaling.fit(points).transform(points)
    assert result.inertia == pytest.approx(((standardized - standardized.mean(axis=0)) ** 2).sum())


def test_as_many_clusters_as_points_gives_zero_inertia():
    assert fit(LINE, k=4).inertia == pytest.approx(0.0)


def test_identical_points():
    points = np.full((5, 2), 3.0)

    assert fit(points, k=1).inertia == 0.0
    with pytest.raises(ValueError, match="distinct points"):
        fit(points, k=2)


def test_same_seed_gives_the_same_result():
    points, _ = blobs()

    first, second = fit(points, k=3, seed=3), fit(points, k=3, seed=3)

    np.testing.assert_array_equal(first.labels, second.labels)
    np.testing.assert_array_equal(first.centroids, second.centroids)


def test_restarts_keep_the_lowest_inertia():
    points, _ = blobs(seed=9)

    single = fit(points, k=3, restarts=1, seed=2)
    many = fit(points, k=3, restarts=10, seed=2)

    assert many.inertia <= single.inertia


def test_new_points_go_to_the_nearest_centre():
    points, _ = blobs()
    result = fit(points, k=3)

    labels = result.predict(np.array(TRUE_CENTRES))

    assert len(set(labels.tolist())) == 3
    assert labels.tolist() == [result.predict(points[i : i + 1])[0] for i in (0, 50, 100)]


# --- Eq. 8: silhouette ---


def test_silhouette_hand_example():
    # Point 0: a = 1, b = (10 + 11) / 2, s = 9.5 / 10.5; point 1: a = 1, b = 9.5, s = 8.5 / 9.5.
    expected = (2 * 9.5 / 10.5 + 2 * 8.5 / 9.5) / 4

    assert silhouette(LINE, np.array([0, 0, 1, 1])) == pytest.approx(expected)
    assert expected == pytest.approx(0.899749, abs=1e-6)


def test_a_point_alone_in_its_cluster_scores_zero():
    points = np.array([[0.0], [10.0], [11.0]])

    # 0 for the lone point, 9/10 and 10/11 for the other two.
    assert silhouette(points, np.array([0, 1, 1])) == pytest.approx((0 + 0.9 + 10 / 11) / 3)


def test_silhouette_needs_between_two_and_n_minus_one_clusters():
    with pytest.raises(ValueError):
        silhouette(LINE, np.array([0, 0, 0, 0]))
    with pytest.raises(ValueError):
        silhouette(LINE, np.array([0, 1, 2, 3]))


def test_well_separated_groups_have_a_high_silhouette():
    points, true_groups = blobs()
    standardized = FeatureScaling.fit(points).transform(points)

    assert silhouette(standardized, true_groups) > 0.7


# --- validation ---


@pytest.mark.parametrize(
    ("features", "k", "options"),
    [
        (LINE, 0, {}),
        (LINE, 5, {}),
        (np.array([[math.nan], [1.0]]), 1, {}),
        (np.array([1.0, 2.0]), 1, {}),
        (LINE, 2, {"restarts": 0}),
        (LINE, 2, {"initial_centroids": np.zeros((3, 1))}),
    ],
)
def test_invalid_input_is_rejected(features, k, options):
    with pytest.raises(ValueError):
        fit(features, k, **options)
