"""Choose the L2 strength of logistic regression on the calibration seasons.

Run from the project folder with ``python -m app.evaluation.logistic_calibration``.

The model runs over the warm-up and calibration seasons only; the evaluation seasons are never
read. Every L2 value of the grid is scored by the log loss, the mean of -ln P(actual result) over
the calibration matches. This is the quantity the model itself minimizes during training, so it
is the natural measure for choosing its penalty. The value with the lowest log loss wins.
"""

import math
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from app.data.models import Match
from app.data.paths import DATABASE_PATH
from app.data.repository import MatchRepository
from app.evaluation.periods import CALIBRATION_SEASONS, WARM_UP_SEASONS
from app.prediction.logistic_predictions import (
    MIN_TRAINING_MATCHES,
    OUTCOME_ORDER,
    run_logistic_regression,
)

COMPETITION = "SP1"
L2_VALUES = (0.0, 0.001, 0.01, 0.1, 1.0)


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    """The score of one L2 value on the calibration matches."""

    l2: float
    log_loss: float
    matches: int


def calibrate(
    matches: Iterable[Match],
    l2_values: Sequence[float] = L2_VALUES,
    warm_up_seasons: Sequence[str] = WARM_UP_SEASONS,
    calibration_seasons: Sequence[str] = CALIBRATION_SEASONS,
    min_training_matches: int = MIN_TRAINING_MATCHES,
) -> list[CalibrationResult]:
    """Score every L2 value on the calibration seasons and return the results, best first."""
    selected = _warm_up_and_calibration(matches, warm_up_seasons, calibration_seasons)
    results = []
    for l2 in l2_values:
        predictions = run_logistic_regression(
            selected, l2=l2, min_training_matches=min_training_matches
        )
        losses = [
            -math.log(p.probabilities[OUTCOME_ORDER.index(p.match.result)])
            for p in predictions
            if p.match.season in calibration_seasons
        ]
        if not losses:
            raise ValueError(
                "no calibration match was predicted; there are too few training matches"
            )
        results.append(
            CalibrationResult(l2=l2, log_loss=math.fsum(losses) / len(losses), matches=len(losses))
        )
    return sorted(results, key=lambda result: (result.log_loss, result.l2))


def constant_frequency_log_loss(
    matches: Iterable[Match],
    warm_up_seasons: Sequence[str] = WARM_UP_SEASONS,
    calibration_seasons: Sequence[str] = CALIBRATION_SEASONS,
) -> float:
    """Reference: always predict the warm-up seasons' frequencies of H, D and A."""
    selected = _warm_up_and_calibration(matches, warm_up_seasons, calibration_seasons)
    warm_up = Counter(match.result for match in selected if match.season in warm_up_seasons)
    if not warm_up:
        raise ValueError("there are no matches from the warm-up seasons")
    total = warm_up.total()
    calibration = [match for match in selected if match.season in calibration_seasons]
    losses = [-math.log(warm_up[match.result] / total) for match in calibration]
    return math.fsum(losses) / len(losses)


def main(
    database_path: Path = DATABASE_PATH,
    competition: str = COMPETITION,
    min_training_matches: int = MIN_TRAINING_MATCHES,
) -> int:
    """Run the grid search and print the results. Returns the process exit code."""
    if not database_path.is_file():
        print(
            f"Database not found: {database_path}\nRun: python -m app.data.build_database",
            file=sys.stderr,
        )
        return 1
    with MatchRepository.open(database_path) as repository:
        matches = repository.matches(competition)
    results = calibrate(matches, min_training_matches=min_training_matches)
    print(
        f"Logistic regression calibration on {competition}: warm-up {', '.join(WARM_UP_SEASONS)}, "
        f"calibration {', '.join(CALIBRATION_SEASONS)} ({results[0].matches} matches)"
    )
    print("     L2    log loss")
    for result in results:
        print(f"{result.l2:7g}    {result.log_loss:.5f}")
    print(f"Reference (warm-up result frequencies): {constant_frequency_log_loss(matches):.5f}")
    print(f"Best: L2 = {results[0].l2:g}")
    return 0


def _warm_up_and_calibration(
    matches: Iterable[Match], warm_up_seasons: Sequence[str], calibration_seasons: Sequence[str]
) -> list[Match]:
    used_seasons = {*warm_up_seasons, *calibration_seasons}
    selected = [match for match in matches if match.season in used_seasons]
    if not any(match.season in calibration_seasons for match in selected):
        raise ValueError("there are no matches from the calibration seasons")
    return selected


if __name__ == "__main__":
    sys.exit(main())
