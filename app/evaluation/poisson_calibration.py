"""Choose the Poisson model's team window N and prior weight m on the calibration seasons.

Run from the project folder with ``python -m app.evaluation.poisson_calibration``.

The model runs over the warm-up and calibration seasons only; the evaluation seasons are never
read. Every (N, m) pair of the grid is scored by the mean of -ln P(actual score) over the
calibration matches: the Poisson model predicts the whole score table, so the probability it gave
to the score that happened is the most direct measure of it. The pair with the lowest value wins.
"""

import math
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from app.algorithms.poisson import score_distribution
from app.data.models import Match
from app.data.paths import DATABASE_PATH
from app.data.repository import MatchRepository
from app.evaluation.periods import CALIBRATION_SEASONS, WARM_UP_SEASONS
from app.prediction.poisson_predictions import LEAGUE_WINDOW, run_poisson
from app.statistics.team_statistics import MatchHistory, league_averages

COMPETITION = "SP1"
TEAM_WINDOWS = (5, 10, 19, 38, 57)
PRIOR_MATCHES = (1, 2, 5, 10, 20, 30, 50, 80)


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    """The score of one (N, m) pair on the calibration matches."""

    team_window: int
    prior_matches: float
    mean_log_loss: float
    matches: int


def calibrate(
    matches: Iterable[Match],
    team_windows: Sequence[int] = TEAM_WINDOWS,
    prior_matches: Sequence[float] = PRIOR_MATCHES,
    warm_up_seasons: Sequence[str] = WARM_UP_SEASONS,
    calibration_seasons: Sequence[str] = CALIBRATION_SEASONS,
) -> list[CalibrationResult]:
    """Score every (N, m) pair on the calibration seasons and return the results, best first."""
    selected = _warm_up_and_calibration(matches, warm_up_seasons, calibration_seasons)
    results = []
    for team_window, prior in product(team_windows, prior_matches):
        losses = [
            -math.log(p.distribution.probabilities[p.match.home_goals, p.match.away_goals])
            for p in run_poisson(selected, team_window=team_window, prior_matches=prior)
            if p.match.season in calibration_seasons
        ]
        results.append(
            CalibrationResult(
                team_window=team_window,
                prior_matches=prior,
                mean_log_loss=math.fsum(losses) / len(losses),
                matches=len(losses),
            )
        )
    return sorted(results, key=lambda r: (r.mean_log_loss, r.team_window, r.prior_matches))


def league_average_log_loss(
    matches: Iterable[Match],
    warm_up_seasons: Sequence[str] = WARM_UP_SEASONS,
    calibration_seasons: Sequence[str] = CALIBRATION_SEASONS,
) -> float:
    """Reference: the same measure when every match gets lambda = the league averages.

    This is the Poisson model without team strengths (every strength equal to 1).
    """
    selected = _warm_up_and_calibration(matches, warm_up_seasons, calibration_seasons)
    history = MatchHistory(selected)
    losses = []
    for match in selected:
        if match.season not in calibration_seasons:
            continue
        league = league_averages(history, match.match_date, last=LEAGUE_WINDOW)
        distribution = score_distribution(league.home_goals_per_match, league.away_goals_per_match)
        losses.append(-math.log(distribution.probabilities[match.home_goals, match.away_goals]))
    return math.fsum(losses) / len(losses)


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
        f"Poisson calibration on {competition}: warm-up {', '.join(WARM_UP_SEASONS)}, "
        f"calibration {', '.join(CALIBRATION_SEASONS)} ({results[0].matches} matches)"
    )
    print("   N     m    mean -ln P(actual score)")
    for result in results[:10]:
        print(f"{result.team_window:4d} {result.prior_matches:5g}    {result.mean_log_loss:.5f}")
    print(
        "Reference without team strengths (league averages): "
        f"{league_average_log_loss(matches):.5f}"
    )
    best = results[0]
    print(f"Best: N = {best.team_window}, m = {best.prior_matches:g}")
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
