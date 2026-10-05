"""Score every model of the prediction log with the evaluation metrics.

Run from the project folder with ``python -m app.evaluation.evaluator [CODE]`` (default SP1) after
``python -m app.evaluation.backtesting`` has written the log of that competition.

All models must cover exactly the same matches, so that they are compared under identical
conditions. "Always home win" gives probability 0 to draws and away wins, so it is scored on
accuracy and the confusion matrix only.
"""

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.evaluation.backtesting import (
    ALWAYS_HOME_WIN,
    MODEL_ORDER,
    PredictionLogRow,
    log_path,
    read_log,
)
from app.evaluation.metrics import (
    CalibrationBin,
    Estimate,
    accuracy,
    brier_score,
    calibration_table,
    confusion_matrix,
    expected_calibration_error,
    log_loss,
    mean_absolute_error,
    outcome_indices,
)

ACCURACY_ONLY = frozenset({ALWAYS_HOME_WIN})


@dataclass(frozen=True, eq=False)
class ModelEvaluation:
    """Every metric of one model over the evaluation matches."""

    model: str
    matches: int
    accuracy: Estimate
    confusion: np.ndarray
    brier: Estimate | None = None
    log_loss: Estimate | None = None
    calibration: tuple[CalibrationBin, ...] | None = None
    calibration_error: float | None = None
    goals_error: Estimate | None = None


def evaluate(rows: Sequence[PredictionLogRow]) -> list[ModelEvaluation]:
    """Score every model of the log, in the order of MODEL_ORDER."""
    by_model: dict[str, list[PredictionLogRow]] = {}
    for row in rows:
        by_model.setdefault(row.model, []).append(row)
    if not by_model:
        raise ValueError("the prediction log is empty")
    match_sets = {
        model: {_match_key(row) for row in model_rows} for model, model_rows in by_model.items()
    }
    reference = next(iter(match_sets.values()))
    if any(matches != reference for matches in match_sets.values()):
        raise ValueError("models cover different matches; they would not be compared fairly")

    order = [model for model in MODEL_ORDER if model in by_model]
    order += sorted(set(by_model) - set(order))
    return [_evaluate_model(model, by_model[model]) for model in order]


def main(log: Path | None = None) -> int:
    """Print the evaluation of the saved log. Returns the process exit code."""
    log = log or log_path()
    if not log.is_file():
        print(
            f"Prediction log not found: {log}\nRun: python -m app.evaluation.backtesting",
            file=sys.stderr,
        )
        return 1
    rows = read_log(log)
    evaluations = evaluate(rows)
    seasons = sorted({row.season for row in rows})
    print(f"Evaluation of {evaluations[0].matches} matches, seasons {seasons[0]} to {seasons[-1]}")
    print("(value ± standard error; Brier score and log loss: lower is better)\n")
    print(
        f"{'model':22s} {'accuracy':>16s} {'Brier score':>17s} {'log loss':>17s} "
        f"{'calibration error':>18s} {'goals error':>15s}"
    )
    for evaluation in evaluations:
        print(
            f"{evaluation.model:22s} {_format(evaluation.accuracy, percent=True):>16s} "
            f"{_format(evaluation.brier):>17s} {_format(evaluation.log_loss):>17s} "
            f"{_plain(evaluation.calibration_error):>18s} {_format(evaluation.goals_error):>15s}"
        )
    print("\nConfusion matrices (rows: actual H, D, A; columns: predicted H, D, A)")
    for evaluation in evaluations:
        cells = " | ".join(" ".join(f"{count:5d}" for count in row) for row in evaluation.confusion)
        print(f"  {evaluation.model:22s} {cells}")
    print("\nCalibration (bin: mean predicted / observed, number of statements)")
    for evaluation in evaluations:
        if evaluation.calibration is None:
            continue
        cells = [
            f"{b.lower:.1f}-{b.upper:.1f}: "
            f"{b.mean_predicted:.3f}/{b.observed_frequency:.3f} ({b.count})"
            for b in evaluation.calibration
            if b.count
        ]
        print(f"  {evaluation.model}:")
        for cell in cells:
            print(f"    {cell}")
    return 0


def _evaluate_model(model: str, rows: Sequence[PredictionLogRow]) -> ModelEvaluation:
    probabilities = np.array([[row.p_home, row.p_draw, row.p_away] for row in rows])
    actual = outcome_indices([row.actual for row in rows])
    result = ModelEvaluation(
        model=model,
        matches=len(rows),
        accuracy=accuracy(probabilities, actual),
        confusion=confusion_matrix(probabilities, actual),
    )
    if model in ACCURACY_ONLY:
        return result
    calibration = tuple(calibration_table(probabilities, actual))
    goals = [row for row in rows if row.expected_home_goals is not None]
    goals_error = None
    if goals:
        expected = [g for row in goals for g in (row.expected_home_goals, row.expected_away_goals)]
        scored = [g for row in goals for g in (row.home_goals, row.away_goals)]
        goals_error = mean_absolute_error(expected, scored)
    return ModelEvaluation(
        model=model,
        matches=len(rows),
        accuracy=result.accuracy,
        confusion=result.confusion,
        brier=brier_score(probabilities, actual),
        log_loss=log_loss(probabilities, actual),
        calibration=calibration,
        calibration_error=expected_calibration_error(calibration),
        goals_error=goals_error,
    )


def _match_key(row: PredictionLogRow) -> tuple:
    return row.match_date, row.home_team, row.away_team


def _format(estimate: Estimate | None, percent: bool = False) -> str:
    if estimate is None:
        return "-"
    pattern = "{:.1%}" if percent else "{:.4f}"
    text = pattern.format(estimate.value)
    if estimate.standard_error is not None:
        text += " ± " + pattern.format(estimate.standard_error)
    return text


def _plain(value: float | None) -> str:
    return "-" if value is None else f"{value:.4f}"


if __name__ == "__main__":
    sys.exit(main(log_path(sys.argv[1]) if len(sys.argv) > 1 else None))
