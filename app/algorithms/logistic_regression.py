"""Multinomial (softmax) logistic regression, implemented from its definition with NumPy.

Notation, as in docs/algorithms/logistic_regression.md:

    n, d, C      numbers of examples, features and classes (C = 3: home win, draw, away win)
    X            n x d feature matrix, standardized with the training rows' means and standard
                 deviations; X~ is X with a first column of ones for the biases
    Y            n x C one-hot targets: Y[i, c] = 1 when example i belongs to class c       (Eq. 1)
    W            (d + 1) x C parameters; row 0 holds the biases
    Z            X~ W, the class scores                                                  (Eq. 2)
    P            softmax of each row of Z: P[i, c] = exp(Z[i, c]) / sum_k exp(Z[i, k])     (Eq. 3)
                 computed after subtracting each row's maximum, which does not change P
    L(W)         -(1/n) sum_i ln P[i, y_i] + (lambda / 2) * ||W without row 0||^2           (Eq. 4)
    grad L(W)    (1/n) X~^T (P - Y) + lambda * W, with row 0 (biases) not penalized       (Eq. 5)
    update       W <- W - eta * grad L(W)                                              (Eq. 6)
                 eta = 1 / (0.5 * l_max(X~^T X~ / n) + lambda), where l_max is the largest
                 eigenvalue; with this step the loss never increases
    stop         when L decreases by less than tol * |L|, or after max_iterations          (Eq. 7)

The loss is convex, so gradient descent approaches its single minimum; the stopping rule only
decides how precisely.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

DEFAULT_TOLERANCE = 1e-8
DEFAULT_MAX_ITERATIONS = 10_000


@dataclass(frozen=True, eq=False)
class Standardizer:
    """Per-feature means and standard deviations, fitted on training rows only."""

    means: np.ndarray
    scales: np.ndarray

    @classmethod
    def fit(cls, features: np.ndarray) -> Standardizer:
        """Measure the training features. A constant feature gets scale 1 and becomes 0."""
        features = _as_feature_matrix(features)
        scales = features.std(axis=0)
        scales[scales == 0] = 1.0
        return cls(means=features.mean(axis=0), scales=scales)

    def transform(self, features: np.ndarray) -> np.ndarray:
        """Return (x - mean) / scale for every row, using the training statistics."""
        features = _as_feature_matrix(features)
        if features.shape[1] != self.means.shape[0]:
            raise ValueError(f"expected {self.means.shape[0]} features, got {features.shape[1]}")
        return (features - self.means) / self.scales


def one_hot(labels: Sequence[int], classes: int) -> np.ndarray:
    """Eq. 1: the n x C target matrix with a single 1 per row, in the column of its class."""
    labels = np.asarray(labels)
    if labels.ndim != 1 or not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("labels must be a one-dimensional sequence of integers")
    if labels.size and (labels.min() < 0 or labels.max() >= classes):
        raise ValueError(f"labels must be between 0 and {classes - 1}")
    targets = np.zeros((labels.size, classes))
    targets[np.arange(labels.size), labels] = 1.0
    return targets


def softmax(scores: np.ndarray) -> np.ndarray:
    """Eq. 3: row-wise softmax, stable for very large scores."""
    shifted = scores - scores.max(axis=1, keepdims=True)
    exponentials = np.exp(shifted)
    return exponentials / exponentials.sum(axis=1, keepdims=True)


def loss(weights: np.ndarray, design: np.ndarray, targets: np.ndarray, l2: float) -> float:
    """Eq. 4: mean cross-entropy plus the L2 penalty on every row of W except the biases.

    ``design`` is X~, the standardized features with a first column of ones.
    """
    scores = design @ weights
    shifted = scores - scores.max(axis=1, keepdims=True)
    log_probabilities = shifted - np.log(np.exp(shifted).sum(axis=1, keepdims=True))
    cross_entropy = -float((targets * log_probabilities).sum()) / design.shape[0]
    return cross_entropy + 0.5 * l2 * float((weights[1:] ** 2).sum())


def gradient(weights: np.ndarray, design: np.ndarray, targets: np.ndarray, l2: float) -> np.ndarray:
    """Eq. 5: (1/n) X~^T (P - Y) + lambda * W, without penalizing the biases (row 0)."""
    probabilities = softmax(design @ weights)
    result = design.T @ (probabilities - targets) / design.shape[0]
    result[1:] += l2 * weights[1:]
    return result


@dataclass(frozen=True, eq=False)
class SoftmaxRegression:
    """A trained model: its parameters, its standardizer and how training went."""

    weights: np.ndarray
    standardizer: Standardizer
    loss_history: tuple[float, ...]
    converged: bool

    @property
    def iterations(self) -> int:
        return len(self.loss_history) - 1

    def predict_probabilities(self, features: np.ndarray) -> np.ndarray:
        """Return the n x C class probabilities for raw (not yet standardized) features."""
        return softmax(_design_matrix(self.standardizer.transform(features)) @ self.weights)


def fit(
    features: np.ndarray,
    labels: Sequence[int],
    *,
    classes: int = 3,
    l2: float = 0.0,
    tolerance: float = DEFAULT_TOLERANCE,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    initial_weights: np.ndarray | None = None,
) -> SoftmaxRegression:
    """Train the model by batch gradient descent (Eq. 6) until the stopping rule (Eq. 7).

    Training starts from zero weights, or from ``initial_weights`` (a warm start, for example
    the previous model's weights when refitting on a slightly larger training set).
    """
    features = _as_feature_matrix(features)
    if classes < 2:
        raise ValueError(f"classes must be at least 2, got {classes}")
    targets = one_hot(labels, classes)
    if targets.shape[0] != features.shape[0] or not features.shape[0]:
        raise ValueError("need the same, non-zero number of feature rows and labels")
    missing_classes = np.flatnonzero(targets.sum(axis=0) == 0).tolist()
    if missing_classes:
        raise ValueError(
            f"classes {missing_classes} have no training examples: the loss would have no "
            "minimum, because their unpenalized biases could decrease without limit"
        )
    if not (np.isfinite(l2) and l2 >= 0):
        raise ValueError(f"l2 must be zero or positive, got {l2}")
    if not tolerance > 0 or max_iterations < 1:
        raise ValueError("tolerance must be positive and max_iterations at least 1")

    standardizer = Standardizer.fit(features)
    design = _design_matrix(standardizer.transform(features))
    shape = (design.shape[1], classes)
    if initial_weights is None:
        weights = np.zeros(shape)
    elif initial_weights.shape != shape:
        raise ValueError(f"initial_weights must have shape {shape}, got {initial_weights.shape}")
    else:
        weights = np.array(initial_weights, dtype=float)

    largest_curvature = 0.5 * np.linalg.eigvalsh(design.T @ design / design.shape[0]).max() + l2
    step = 1.0 / largest_curvature
    history = [loss(weights, design, targets, l2)]
    converged = False
    for _ in range(max_iterations):
        weights = weights - step * gradient(weights, design, targets, l2)
        history.append(loss(weights, design, targets, l2))
        if history[-2] - history[-1] < tolerance * abs(history[-2]):
            converged = True
            break
    weights.setflags(write=False)
    return SoftmaxRegression(
        weights=weights,
        standardizer=standardizer,
        loss_history=tuple(history),
        converged=converged,
    )


def _design_matrix(standardized: np.ndarray) -> np.ndarray:
    """Eq. 2's X~: the standardized features with a first column of ones for the biases."""
    return np.column_stack([np.ones(standardized.shape[0]), standardized])


def _as_feature_matrix(features: np.ndarray) -> np.ndarray:
    features = np.array(features, dtype=float)
    if features.ndim != 2:
        raise ValueError("features must be a two-dimensional n x d matrix")
    if not np.isfinite(features).all():
        raise ValueError("features must be finite numbers")
    return features
