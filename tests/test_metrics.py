import math

import numpy as np
import pytest

from app.evaluation.metrics import (
    accuracy,
    brier_score,
    calibration_table,
    confident_accuracy,
    confusion_matrix,
    expected_calibration_error,
    log_loss,
    mean_absolute_error,
    outcome_indices,
)

H, D, A = 0, 1, 2
# Four forecasts and what happened: worked through by hand in the tests below.
FORECASTS = np.array(
    [
        [0.5, 0.3, 0.2],  # home win happened, home win predicted
        [0.2, 0.5, 0.3],  # away win happened, draw predicted
        [0.6, 0.2, 0.2],  # home win happened, home win predicted
        [1 / 3, 1 / 3, 1 / 3],  # draw happened, the tie goes to the home win
    ]
)
ACTUAL = np.array([H, A, H, D])


def test_outcome_codes_become_indices():
    assert outcome_indices(["H", "D", "A", "H"]).tolist() == [0, 1, 2, 0]
    with pytest.raises(ValueError):
        outcome_indices(["H", "X"])


def test_accuracy_hand_example():
    result = accuracy(FORECASTS, ACTUAL)

    # Correct: 1, 0, 1, 0. Standard error: sqrt(1/3) / sqrt(4).
    assert (result.value, result.count) == (0.5, 4)
    assert result.standard_error == pytest.approx(math.sqrt(1 / 3) / 2)


def test_brier_score_hand_example():
    # 0.25 + 0.09 + 0.04 = 0.38;  0.04 + 0.25 + 0.49 = 0.78;  0.16 + 0.04 + 0.04 = 0.24;
    # 2 * (1/3)^2 + (2/3)^2 = 2/3.
    expected = (0.38 + 0.78 + 0.24 + 2 / 3) / 4

    assert brier_score(FORECASTS, ACTUAL).value == pytest.approx(expected)
    assert expected == pytest.approx(0.516667, abs=1e-6)


def test_log_loss_hand_example():
    expected = (-math.log(0.5) - math.log(0.3) - math.log(0.6) + math.log(3)) / 4

    assert log_loss(FORECASTS, ACTUAL).value == pytest.approx(expected)
    assert expected == pytest.approx(0.876640, abs=1e-6)


def test_confident_accuracy_hand_example():
    # largest probabilities 0.5, 0.5, 0.6 and 1/3; right, wrong, right, wrong
    at_half = confident_accuracy(FORECASTS, ACTUAL, 0.5)
    assert (at_half.matches, at_half.share) == (3, 0.75)
    assert at_half.accuracy.value == pytest.approx(2 / 3)
    sixty = confident_accuracy(FORECASTS, ACTUAL, 0.6)
    assert (sixty.matches, sixty.accuracy.value, sixty.accuracy.standard_error) == (1, 1.0, None)
    none = confident_accuracy(FORECASTS, ACTUAL, 0.7)
    assert (none.matches, none.share, none.accuracy) == (0, 0.0, None)
    everything = confident_accuracy(FORECASTS, ACTUAL, 1 / 3)
    assert everything.accuracy.value == pytest.approx(0.5)  # the plain accuracy


@pytest.mark.parametrize("threshold", [0, -0.1, 1.2])
def test_a_confidence_threshold_is_a_probability(threshold):
    with pytest.raises(ValueError, match="threshold"):
        confident_accuracy(FORECASTS, ACTUAL, threshold)


def test_confusion_matrix_hand_example():
    # Rows: actual H, D, A. Columns: predicted H, D, A.
    np.testing.assert_array_equal(
        confusion_matrix(FORECASTS, ACTUAL), [[2, 0, 0], [1, 0, 0], [0, 1, 0]]
    )


def test_calibration_hand_example_with_two_bins():
    table = calibration_table(FORECASTS, ACTUAL, bins=2)

    # Below 0.5: nine statements (0.3, 0.2, 0.2, 0.3, 0.2, 0.2 and three times 1/3), two came true.
    # From 0.5: 0.5 (true), 0.5 (false), 0.6 (true).
    low, high = table
    assert (low.lower, low.upper, low.count) == (0.0, 0.5, 9)
    assert low.mean_predicted == pytest.approx(2.4 / 9)
    assert low.observed_frequency == pytest.approx(2 / 9)
    assert (high.count, high.mean_predicted, high.observed_frequency) == pytest.approx(
        (3, 1.6 / 3, 2 / 3)
    )
    # (9/12) * |2.4/9 - 2/9| + (3/12) * |1.6/3 - 2/3| = 1/30 + 1/30
    assert expected_calibration_error(table) == pytest.approx(1 / 15)


def test_empty_calibration_bins_have_no_averages():
    table = calibration_table(np.array([[1.0, 0.0, 0.0]]), np.array([H]), bins=10)

    assert [bin_.count for bin_ in table] == [2] + [0] * 8 + [1]
    assert table[5].mean_predicted is None
    assert table[9].observed_frequency == 1.0


def test_a_perfect_forecaster():
    perfect = np.eye(3)[ACTUAL]

    assert accuracy(perfect, ACTUAL).value == 1.0
    assert brier_score(perfect, ACTUAL).value == 0.0
    assert log_loss(perfect, ACTUAL).value == 0.0
    assert expected_calibration_error(calibration_table(perfect, ACTUAL)) == 0.0


def test_uniform_forecasts_score_two_thirds_and_ln_3():
    uniform = np.full((4, 3), 1 / 3)

    assert brier_score(uniform, ACTUAL).value == pytest.approx(2 / 3)
    assert log_loss(uniform, ACTUAL).value == pytest.approx(math.log(3))


def test_log_loss_is_infinite_for_a_zero_probability_that_came_true():
    always_home = np.tile([1.0, 0.0, 0.0], (4, 1))

    with pytest.raises(ValueError, match="infinite"):
        log_loss(always_home, ACTUAL)
    assert log_loss(always_home[[0, 2]], ACTUAL[[0, 2]]).value == 0.0


def test_mean_absolute_error_of_expected_goals():
    result = mean_absolute_error([1.5, 0.5, 2.0], [2, 0, 2])

    assert result.value == pytest.approx(1 / 3)
    assert result.count == 3


def test_a_single_match_has_no_standard_error():
    assert accuracy(FORECASTS[:1], ACTUAL[:1]).standard_error is None


@pytest.mark.parametrize(
    ("probabilities", "actual"),
    [
        (np.zeros((0, 3)), np.array([], dtype=int)),
        (np.array([[0.5, 0.5]]), np.array([H])),
        (np.array([[0.5, 0.3, 0.3]]), np.array([H])),
        (np.array([[1.2, -0.1, -0.1]]), np.array([H])),
        (np.array([[0.5, 0.3, 0.2]]), np.array([3])),
        (np.array([[0.5, 0.3, 0.2]]), np.array([H, D])),
        (np.array([[0.5, 0.3, 0.2]]), np.array([0.0])),
    ],
)
def test_invalid_forecasts_are_rejected(probabilities, actual):
    with pytest.raises(ValueError):
        brier_score(probabilities, actual)


@pytest.mark.parametrize(
    ("expected", "actual"), [([], []), ([1.0], [1.0, 2.0]), ([math.nan], [1.0])]
)
def test_invalid_mean_absolute_error_input(expected, actual):
    with pytest.raises(ValueError):
        mean_absolute_error(expected, actual)


def test_calibration_needs_at_least_one_bin():
    with pytest.raises(ValueError):
        calibration_table(FORECASTS, ACTUAL, bins=0)
