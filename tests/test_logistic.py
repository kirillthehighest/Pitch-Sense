import math

import numpy as np
import pytest

from app.algorithms.logistic_regression import (
    Standardizer,
    fit,
    gradient,
    loss,
    one_hot,
    softmax,
)

HOME_WIN, DRAW, AWAY_WIN = 0, 1, 2


def design(features: np.ndarray) -> np.ndarray:
    """X~ for already standardized test features."""
    return np.column_stack([np.ones(len(features)), features])


def simulated(rows: int, true_weights: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Standard-normal features and labels drawn from the softmax of their true scores."""
    generator = np.random.default_rng(seed)
    features = generator.standard_normal((rows, true_weights.shape[0] - 1))
    probabilities = softmax(design(features) @ true_weights)
    cumulative = probabilities.cumsum(axis=1)
    labels = (generator.random(rows)[:, None] > cumulative).sum(axis=1)
    return features, labels


# --- Eq. 1 and 3: targets and softmax ---


def test_one_hot_targets():
    targets = one_hot([HOME_WIN, AWAY_WIN, DRAW], classes=3)

    np.testing.assert_array_equal(targets, [[1, 0, 0], [0, 0, 1], [0, 1, 0]])


@pytest.mark.parametrize("labels", [[0, 3], [-1], [0.5]])
def test_one_hot_rejects_invalid_labels(labels):
    with pytest.raises(ValueError):
        one_hot(labels, classes=3)


def test_softmax_hand_values():
    probabilities = softmax(np.array([[0.0, 0.0, 0.0], [0.0, math.log(2), math.log(3)]]))

    np.testing.assert_allclose(probabilities, [[1 / 3, 1 / 3, 1 / 3], [1 / 6, 2 / 6, 3 / 6]])


def test_softmax_ignores_a_shift_of_all_scores_and_survives_huge_scores():
    scores = np.array([[1000.0, 1000.0, 0.0], [-1000.0, -999.0, -1001.0]])

    probabilities = softmax(scores)

    assert np.isfinite(probabilities).all()
    np.testing.assert_allclose(probabilities[0], [0.5, 0.5, 0.0], atol=1e-12)
    np.testing.assert_allclose(probabilities[1], softmax(np.array([[-1.0, 0.0, -2.0]]))[0])
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0)


# --- Eq. 4 and 5: loss and gradient ---


def test_loss_with_zero_weights_is_ln_3():
    features = np.array([[0.5, -1.0], [1.5, 2.0], [-0.3, 0.0]])
    targets = one_hot([HOME_WIN, DRAW, AWAY_WIN], 3)

    assert loss(np.zeros((3, 3)), design(features), targets, l2=0.7) == pytest.approx(math.log(3))


def test_gradient_of_the_biases_at_zero_weights():
    # Uniform predictions minus the class frequencies (1/2, 1/4, 1/4).
    features = np.array([[0.0], [0.0], [0.0], [0.0]])
    targets = one_hot([HOME_WIN, HOME_WIN, DRAW, AWAY_WIN], 3)

    bias_gradient = gradient(np.zeros((2, 3)), design(features), targets, l2=0.0)[0]

    np.testing.assert_allclose(bias_gradient, [1 / 3 - 1 / 2, 1 / 3 - 1 / 4, 1 / 3 - 1 / 4])


def test_gradient_matches_a_numerical_estimate():
    generator = np.random.default_rng(5)
    features = generator.standard_normal((40, 4))
    targets = one_hot(generator.integers(0, 3, size=40), 3)
    weights = generator.standard_normal((5, 3))
    step = 1e-6

    numerical = np.zeros_like(weights)
    for index in np.ndindex(weights.shape):
        nudge = np.zeros_like(weights)
        nudge[index] = step
        numerical[index] = (
            loss(weights + nudge, design(features), targets, 0.1)
            - loss(weights - nudge, design(features), targets, 0.1)
        ) / (2 * step)

    analytical = gradient(weights, design(features), targets, l2=0.1)
    np.testing.assert_allclose(analytical, numerical, rtol=1e-5, atol=1e-8)


# --- standardization ---


def test_standardizer_uses_the_training_statistics():
    standardizer = Standardizer.fit(np.array([[0.0, 5.0], [2.0, 5.0]]))

    transformed = standardizer.transform(np.array([[3.0, 9.0]]))

    np.testing.assert_allclose(transformed, [[2.0, 4.0]])  # (3 - 1) / 1; constant feature: 9 - 5


def test_standardizer_rejects_a_different_number_of_features():
    with pytest.raises(ValueError, match="expected 2 features"):
        Standardizer.fit(np.zeros((3, 2))).transform(np.zeros((1, 3)))


# --- Eq. 6 and 7: training ---


@pytest.fixture(scope="module")
def known_problem():
    true_weights = np.array([[0.3, -0.2, -0.1], [1.2, 0.0, -1.2], [-0.5, 0.4, 0.1]])
    features, labels = simulated(20_000, true_weights, seed=11)
    return true_weights, features, labels, fit(features, labels)


def test_loss_never_increases_and_training_converges(known_problem):
    *_, model = known_problem
    history = np.array(model.loss_history)

    assert model.converged
    assert history[0] == pytest.approx(math.log(3))
    assert (np.diff(history) <= 1e-12).all()
    assert history[-1] < history[0]


def test_training_recovers_known_weights(known_problem):
    true_weights, features, labels, model = known_problem

    # Adding the same number to every class's weight leaves softmax unchanged, so compare the
    # weights after centring each row. Features are already standardized, so the spaces match.
    def centred(weights):
        return weights - weights.mean(axis=1, keepdims=True)

    np.testing.assert_allclose(centred(model.weights), centred(true_weights), atol=0.1)


def test_predicted_probabilities_are_valid(known_problem):
    _, features, _, model = known_problem

    probabilities = model.predict_probabilities(features[:100])

    assert probabilities.shape == (100, 3)
    assert (probabilities >= 0).all()
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0)


def test_softmax_can_make_draws_most_likely_between_two_extremes():
    positions = np.linspace(-3, 3, 61)
    labels = np.where(positions > 1, HOME_WIN, np.where(positions < -1, AWAY_WIN, DRAW))

    model = fit(positions[:, None], labels, l2=0.01)

    probabilities = model.predict_probabilities(np.array([[-2.5], [0.0], [2.5]]))
    assert probabilities.argmax(axis=1).tolist() == [AWAY_WIN, DRAW, HOME_WIN]


def test_l2_penalty_shrinks_the_weights(known_problem):
    _, features, labels, unpenalized = known_problem

    penalized = fit(features, labels, l2=1.0)

    assert np.linalg.norm(penalized.weights[1:]) < np.linalg.norm(unpenalized.weights[1:])


def test_training_is_deterministic():
    features, labels = simulated(500, np.array([[0.0, 0.1, 0.0], [1.0, 0.0, -1.0]]), seed=3)

    first = fit(features, labels)
    second = fit(features, labels)

    np.testing.assert_array_equal(first.weights, second.weights)
    assert first.loss_history == second.loss_history


def test_max_iterations_stops_training_early():
    features, labels = simulated(500, np.array([[0.0, 0.1, 0.0], [1.0, 0.0, -1.0]]), seed=3)

    model = fit(features, labels, max_iterations=3)

    assert (model.iterations, model.converged, len(model.loss_history)) == (3, False, 4)


def test_warm_start_from_the_solution_converges_immediately(known_problem):
    _, features, labels, model = known_problem

    refitted = fit(features, labels, initial_weights=model.weights)

    assert refitted.converged
    assert refitted.iterations <= 2


def test_a_constant_feature_does_not_break_training():
    features = np.column_stack([np.linspace(-1, 1, 30), np.full(30, 4.0)])
    labels = np.where(
        features[:, 0] > 0.3, HOME_WIN, np.where(features[:, 0] < -0.3, AWAY_WIN, DRAW)
    )

    model = fit(features, labels, l2=0.1)

    assert np.isfinite(model.weights).all()
    assert np.isfinite(model.predict_probabilities(features)).all()


def test_a_class_without_examples_is_refused():
    # Without any draw, the draw bias could fall forever: the loss has no minimum.
    with pytest.raises(ValueError, match=r"classes \[1\] have no training examples"):
        fit(np.array([[0.0], [1.0], [2.0]]), [HOME_WIN, AWAY_WIN, HOME_WIN])


@pytest.mark.parametrize(
    ("features", "labels", "options"),
    [
        (np.zeros((3, 2)), [0, 1], {}),
        (np.zeros((0, 2)), [], {}),
        (np.array([[math.nan, 1.0]]), [0], {}),
        (np.zeros((2, 2)), [0, 5], {}),
        (np.zeros((2, 2)), [0, 1], {"l2": -1.0}),
        (np.zeros((2, 2)), [0, 1], {"tolerance": 0.0}),
        (np.zeros((2, 2)), [0, 1], {"initial_weights": np.zeros((2, 2))}),
        (np.zeros(4), [0, 1, 2, 0], {}),
    ],
)
def test_invalid_training_input_is_rejected(features, labels, options):
    with pytest.raises(ValueError):
        fit(features, labels, **options)
