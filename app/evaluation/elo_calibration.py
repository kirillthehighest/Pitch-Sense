"""Choose the Elo parameters K and H on the calibration seasons.

Run from the project folder with ``python -m app.evaluation.elo_calibration``.

Elo runs over the warm-up and calibration seasons only; the evaluation seasons are never read.
Every (K, H) pair of the grid is scored by the mean squared error between the actual score S_home
and the expected score E_home over the calibration matches, and the pair with the smallest error
is chosen.
"""

import math
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from app.algorithms.elo import actual_score
from app.data.models import Match
from app.data.paths import DATABASE_PATH
from app.data.repository import MatchRepository
from app.evaluation.periods import CALIBRATION_SEASONS, WARM_UP_SEASONS
from app.prediction.elo_predictions import run_elo

COMPETITION = "SP1"
K_FACTORS = (10, 15, 20, 25, 30, 35, 40)
HOME_ADVANTAGES = (0, 20, 40, 60, 80, 100, 120, 140, 160)


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    """The score of one (K, H) pair on the calibration matches."""

    k_factor: float
    home_advantage: float
    mean_squared_error: float
    matches: int


def calibrate(
    matches: Iterable[Match],
    k_factors: Sequence[float] = K_FACTORS,
    home_advantages: Sequence[float] = HOME_ADVANTAGES,
    warm_up_seasons: Sequence[str] = WARM_UP_SEASONS,
    calibration_seasons: Sequence[str] = CALIBRATION_SEASONS,
) -> list[CalibrationResult]:
    """Score every (K, H) pair on the calibration seasons and return the results, best first."""
    used_seasons = {*warm_up_seasons, *calibration_seasons}
    selected = [match for match in matches if match.season in used_seasons]
    if not any(match.season in calibration_seasons for match in selected):
        raise ValueError("there are no matches from the calibration seasons")
    results = []
    for k_factor, home_advantage in product(k_factors, home_advantages):
        run = run_elo(selected, k_factor=k_factor, home_advantage=home_advantage)
        squared_errors = [
            (actual_score(p.match.home_goals, p.match.away_goals) - p.expected_home_score) ** 2
            for p in run.predictions
            if p.match.season in calibration_seasons
        ]
        results.append(
            CalibrationResult(
                k_factor=k_factor,
                home_advantage=home_advantage,
                mean_squared_error=math.fsum(squared_errors) / len(squared_errors),
                matches=len(squared_errors),
            )
        )
    return sorted(results, key=lambda r: (r.mean_squared_error, r.k_factor, r.home_advantage))


def constant_prediction_error(
    matches: Iterable[Match],
    warm_up_seasons: Sequence[str] = WARM_UP_SEASONS,
    calibration_seasons: Sequence[str] = CALIBRATION_SEASONS,
) -> float:
    """Reference error: always predict the warm-up seasons' average home score, with no ratings."""
    matches = list(matches)
    warm_up = [
        actual_score(m.home_goals, m.away_goals) for m in matches if m.season in warm_up_seasons
    ]
    calibration = [
        actual_score(m.home_goals, m.away_goals) for m in matches if m.season in calibration_seasons
    ]
    if not warm_up or not calibration:
        raise ValueError("need matches from both the warm-up and the calibration seasons")
    constant = math.fsum(warm_up) / len(warm_up)
    return math.fsum((score - constant) ** 2 for score in calibration) / len(calibration)


def main(database_path: Path = DATABASE_PATH, competition: str = COMPETITION) -> int:
    """Run the grid search and print the best pairs. Returns the process exit code."""
    if not database_path.is_file():
        print(
            f"Database not found: {database_path}\nRun: python -m app.data.build_database",
            file=sys.stderr,
        )
        return 1
    with MatchRepository.open(database_path) as repository:
        matches = repository.matches(competition)
    results = calibrate(matches)
    print(
        f"Elo calibration on {competition}: warm-up {', '.join(WARM_UP_SEASONS)}, "
        f"calibration {', '.join(CALIBRATION_SEASONS)} ({results[0].matches} matches)"
    )
    print("   K      H    mean squared error")
    for result in results[:10]:
        print(f"{result.k_factor:4g} {result.home_advantage:6g}    {result.mean_squared_error:.5f}")
    print(
        f"Reference without ratings (constant prediction): {constant_prediction_error(matches):.5f}"
    )
    best = results[0]
    print(f"Best: K = {best.k_factor:g}, H = {best.home_advantage:g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
