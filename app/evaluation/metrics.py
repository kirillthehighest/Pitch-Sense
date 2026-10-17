"""Evaluation metrics for home/draw/away forecasts, implemented with NumPy.

Notation, as in docs/evaluation.md: n matches; for match i the forecast p_i = (p_iH, p_iD, p_iA)
and the actual outcome y_i (index 0 = home win, 1 = draw, 2 = away win, one-hot vector e_i).

    accuracy               share of matches whose most likely outcome happened; ties go to the
                           home win, then the draw
    Brier score            (1/n) sum_i sum_c (p_ic - e_ic)^2, between 0 (perfect) and 2
    log loss               (1/n) sum_i -ln p_{i, y_i}; infinite if an outcome that happened had
                           probability 0
    confusion matrix       counts of (actual outcome, predicted outcome)
    calibration            every (match, outcome) pair is one probabilistic statement; within
                           each probability bin, the mean predicted probability is compared with
                           how often the outcome happened
    calibration error      sum_b (N_b / N) |mean predicted_b - observed_b| over the bins (ECE)
    mean absolute error    (1/n) sum |expected - actual|, for expected goals
    confident accuracy     accuracy over the matches whose largest probability max_c p_ic is at
                           least a threshold t (Phase 23), with how many matches that is

Averages come with their standard error: the standard deviation of the per-match values divided
by sqrt(n).
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

OUTCOME_CODES = ("H", "D", "A")
PROBABILITY_TOLERANCE = 1e-6
DEFAULT_CALIBRATION_BINS = 10
# The thresholds of "confident" forecasts the evaluation reports (Phase 23)
CONFIDENCE_THRESHOLDS = (0.5, 0.6, 0.65, 0.7)


@dataclass(frozen=True, slots=True)
class Estimate:
    """An average over matches with its standard error (None when there is a single match)."""

    value: float
    standard_error: float | None
    count: int


@dataclass(frozen=True, slots=True)
class CalibrationBin:
    """One probability bin: how many statements fell in it and how well they matched reality."""

    lower: float
    upper: float
    count: int
    mean_predicted: float | None
    observed_frequency: float | None


@dataclass(frozen=True, slots=True)
class ConfidentAccuracy:
    """How often the most likely outcome happened among the forecasts at least ``threshold``
    sure of it: ``matches`` such forecasts, ``share`` of all; ``accuracy`` None without any."""

    threshold: float
    matches: int
    share: float
    accuracy: Estimate | None


def outcome_indices(codes: Sequence[str]) -> np.ndarray:
    """Turn result codes H, D, A into class indices 0, 1, 2."""
    try:
        return np.array([OUTCOME_CODES.index(code) for code in codes], dtype=int)
    except ValueError:
        raise ValueError(f"result codes must be H, D or A, got {sorted(set(codes))}") from None


def correct_per_match(probabilities: np.ndarray, actual: Sequence[int]) -> np.ndarray:
    """1 for every match whose most likely outcome happened, otherwise 0."""
    probabilities, actual = _checked(probabilities, actual)
    return (probabilities.argmax(axis=1) == actual).astype(float)


def brier_per_match(probabilities: np.ndarray, actual: Sequence[int]) -> np.ndarray:
    """The squared distance between each forecast and its one-hot outcome."""
    probabilities, actual = _checked(probabilities, actual)
    return ((probabilities - np.eye(3)[actual]) ** 2).sum(axis=1)


def log_loss_per_match(probabilities: np.ndarray, actual: Sequence[int]) -> np.ndarray:
    """-ln(probability given to the outcome that happened), for each match."""
    probabilities, actual = _checked(probabilities, actual)
    given = probabilities[np.arange(actual.size), actual]
    if (given <= 0).any():
        raise ValueError("log loss is infinite: an outcome that happened had probability 0")
    return -np.log(given)


def accuracy(probabilities: np.ndarray, actual: Sequence[int]) -> Estimate:
    """The share of matches whose most likely outcome happened."""
    return estimate(correct_per_match(probabilities, actual))


def brier_score(probabilities: np.ndarray, actual: Sequence[int]) -> Estimate:
    """The mean squared distance between the forecast and the one-hot outcome (0 is perfect)."""
    return estimate(brier_per_match(probabilities, actual))


def log_loss(probabilities: np.ndarray, actual: Sequence[int]) -> Estimate:
    """The mean of -ln(probability given to the outcome that happened)."""
    return estimate(log_loss_per_match(probabilities, actual))


def confident_accuracy(
    probabilities: np.ndarray, actual: Sequence[int], threshold: float
) -> ConfidentAccuracy:
    """Accuracy over the matches whose largest probability is at least ``threshold``."""
    if not 0 < threshold <= 1:
        raise ValueError(f"threshold must be in (0, 1], got {threshold}")
    probabilities, actual = _checked(probabilities, actual)
    sure = probabilities.max(axis=1) >= threshold
    count = int(sure.sum())
    return ConfidentAccuracy(
        threshold=threshold,
        matches=count,
        share=count / len(actual),
        accuracy=estimate(correct_per_match(probabilities[sure], actual[sure])) if count else None,
    )


def confusion_matrix(probabilities: np.ndarray, actual: Sequence[int]) -> np.ndarray:
    """A 3 x 3 count matrix: rows are actual outcomes, columns predicted ones (H, D, A)."""
    probabilities, actual = _checked(probabilities, actual)
    matrix = np.zeros((3, 3), dtype=int)
    np.add.at(matrix, (actual, probabilities.argmax(axis=1)), 1)
    return matrix


def calibration_table(
    probabilities: np.ndarray, actual: Sequence[int], bins: int = DEFAULT_CALIBRATION_BINS
) -> list[CalibrationBin]:
    """Group all (match, outcome) probabilities into equal-width bins and compare with reality.

    A probability p falls in bin floor(p * bins); p = 1 goes to the last bin.
    """
    if bins < 1:
        raise ValueError(f"bins must be at least 1, got {bins}")
    probabilities, actual = _checked(probabilities, actual)
    predicted = probabilities.ravel()
    happened = np.eye(3)[actual].ravel()
    indices = np.minimum((predicted * bins).astype(int), bins - 1)
    table = []
    for index in range(bins):
        inside = indices == index
        count = int(inside.sum())
        table.append(
            CalibrationBin(
                lower=index / bins,
                upper=(index + 1) / bins,
                count=count,
                mean_predicted=float(predicted[inside].mean()) if count else None,
                observed_frequency=float(happened[inside].mean()) if count else None,
            )
        )
    return table


def expected_calibration_error(table: Sequence[CalibrationBin]) -> float:
    """The bin-size-weighted mean gap between predicted probability and observed frequency."""
    total = sum(bin_.count for bin_ in table)
    if not total:
        raise ValueError("the calibration table is empty")
    return math.fsum(
        bin_.count / total * abs(bin_.mean_predicted - bin_.observed_frequency)
        for bin_ in table
        if bin_.count
    )


def mean_absolute_error(expected: Sequence[float], actual: Sequence[float]) -> Estimate:
    """The mean absolute difference between expected and actual values (for example goals)."""
    expected, actual = np.asarray(expected, dtype=float), np.asarray(actual, dtype=float)
    if expected.shape != actual.shape or expected.ndim != 1 or not expected.size:
        raise ValueError("need two non-empty sequences of the same length")
    if not (np.isfinite(expected).all() and np.isfinite(actual).all()):
        raise ValueError("values must be finite numbers")
    return estimate(np.abs(expected - actual))


def estimate(values: np.ndarray) -> Estimate:
    """The mean of per-match values with its standard error."""
    count = values.size
    standard_error = float(values.std(ddof=1) / math.sqrt(count)) if count > 1 else None
    return Estimate(value=float(values.mean()), standard_error=standard_error, count=count)


def _checked(probabilities: np.ndarray, actual: Sequence[int]) -> tuple[np.ndarray, np.ndarray]:
    probabilities = np.asarray(probabilities, dtype=float)
    actual = np.asarray(actual)
    if probabilities.ndim != 2 or probabilities.shape[1] != 3 or not probabilities.shape[0]:
        raise ValueError("probabilities must be a non-empty n x 3 matrix (home, draw, away)")
    if actual.shape != (probabilities.shape[0],) or not np.issubdtype(actual.dtype, np.integer):
        raise ValueError("actual must hold one integer outcome index per match")
    if actual.min() < 0 or actual.max() > 2:
        raise ValueError("outcome indices must be 0 (home), 1 (draw) or 2 (away)")
    if not np.isfinite(probabilities).all() or (probabilities < 0).any():
        raise ValueError("probabilities must be non-negative numbers")
    if (np.abs(probabilities.sum(axis=1) - 1) > PROBABILITY_TOLERANCE).any():
        raise ValueError("every forecast must sum to 1")
    return probabilities, actual
