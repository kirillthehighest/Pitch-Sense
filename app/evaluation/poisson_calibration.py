"""Choose the Poisson model's team window N, prior weight m, half-life h and Dixon-Coles rho on
the calibration seasons.

Run from the project folder with ``python -m app.evaluation.poisson_calibration [CODE]``
(default SP1). The grid of N is sized to the league: 5 and 10 matches, then one to five seasons
of a team's home matches (19 to 95 in a 20-team league; 17 to 85 with 18 teams). The grid reached
three seasons until the Premier League and the Bundesliga chose its top value (Phase 15). The
half-lives (Phase 23) are a quarter, a half, one, two and four seasons of home matches, or none
(equal weights; four seasons were added when the Bundesliga chose two, the longest at first);
rho runs from 0 (no correction) to -0.2.

The model runs over the warm-up and calibration seasons only; the evaluation seasons are never
read. Every (N, m, h, rho) choice of the grid is scored by the mean of -ln P(actual score) over
the calibration matches: the Poisson model predicts the whole score table, so the probability it
gave to the score that happened is the most direct measure of it. The choice with the lowest
value wins. rho changes only the four low scores and never the normalisation (Eq. 6), so each
(N, m, h) runs once and every rho rescales its probabilities of 0-0, 0-1, 1-0 and 1-1.
"""

import math
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from app.algorithms.poisson import (
    ScoreDistribution,
    admissible_rho,
    low_score_correction,
    score_distribution,
)
from app.data.competitions import competition as league_of
from app.data.models import Match
from app.data.paths import DATABASE_PATH
from app.data.repository import MatchRepository
from app.evaluation.periods import CALIBRATION_SEASONS, WARM_UP_SEASONS
from app.prediction.poisson_predictions import run_poisson
from app.prediction.settings import PoissonSettings
from app.statistics.team_statistics import MatchHistory, league_averages

COMPETITION = "SP1"
PRIOR_MATCHES = (1, 2, 5, 10, 20, 30, 50, 80)
RHO_VALUES = tuple(-step / 50 for step in range(11))  # 0, -0.02, ..., -0.2


def team_windows(venue_season_length: int) -> tuple[int, ...]:
    """The N grid: 5, 10, then one to five seasons of a team's home matches."""
    return (5, 10, *(seasons * venue_season_length for seasons in range(1, 6)))


def half_lives(venue_season_length: int) -> tuple[float | None, ...]:
    """The h grid: equal weights, then a quarter, a half, one, two and four seasons of home
    matches."""
    return (None, *(round(share * venue_season_length) for share in (0.25, 0.5, 1, 2, 4)))


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    """The score of one (N, m, h, rho) choice on the calibration matches."""

    team_window: int
    prior_matches: float
    half_life: float | None
    rho: float
    mean_log_loss: float
    matches: int

    def settings(self, league_window: int) -> PoissonSettings:
        return PoissonSettings(
            self.team_window, self.prior_matches, league_window, self.half_life, self.rho
        )


def calibrate(
    matches: Iterable[Match],
    windows: Sequence[int] | None = None,
    prior_matches: Sequence[float] = PRIOR_MATCHES,
    warm_up_seasons: Sequence[str] = WARM_UP_SEASONS,
    calibration_seasons: Sequence[str] = CALIBRATION_SEASONS,
    half_life_values: Sequence[float | None] | None = None,
    rho_values: Sequence[float] = RHO_VALUES,
) -> list[CalibrationResult]:
    """Score every (N, m, h, rho) choice on the calibration seasons, best first.

    Without ``windows`` or ``half_life_values`` the grids of the matches' league are used
    (``team_windows``, ``half_lives``).
    """
    selected = _warm_up_and_calibration(matches, warm_up_seasons, calibration_seasons)
    league = league_of(selected[0].competition)
    windows = windows or team_windows(league.venue_season_length)
    if half_life_values is None:
        half_life_values = half_lives(league.venue_season_length)
    results = []
    for team_window, prior, half_life in product(windows, prior_matches, half_life_values):
        settings = PoissonSettings(team_window, prior, league.season_length, half_life)
        scored = [
            (p.match.home_goals, p.match.away_goals, p.distribution)
            for p in run_poisson(selected, settings)
            if p.match.season in calibration_seasons
        ]
        for rho in rho_values:
            losses = [-math.log(_corrected(home, away, table, rho)) for home, away, table in scored]
            results.append(
                CalibrationResult(
                    team_window=team_window,
                    prior_matches=prior,
                    half_life=half_life,
                    rho=rho,
                    mean_log_loss=math.fsum(losses) / len(losses),
                    matches=len(losses),
                )
            )
    return sorted(
        results,
        key=lambda r: (
            r.mean_log_loss,
            r.team_window,
            r.prior_matches,
            r.half_life is not None,
            r.half_life or 0,
            -r.rho,
        ),
    )


def _corrected(
    home_goals: int, away_goals: int, distribution: ScoreDistribution, rho: float
) -> float:
    """P(actual score) of an uncorrected table after the Dixon-Coles correction with ``rho``
    (Eq. 6): the same as ``score_distribution(..., rho=rho)`` gives, without building it."""
    probability = float(distribution.probabilities[home_goals, away_goals])
    if home_goals > 1 or away_goals > 1:
        return probability
    home, away = distribution.home_expected_goals, distribution.away_expected_goals
    tau = low_score_correction(home, away, admissible_rho(home, away, rho))
    return probability * float(tau[home_goals, away_goals])


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
    window = league_of(selected[0].competition).season_length
    losses = []
    for match in selected:
        if match.season not in calibration_seasons:
            continue
        league = league_averages(history, match.match_date, last=window)
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
    print("   N     m     h     rho    mean -ln P(actual score)")
    for result in results[:10]:
        print(
            f"{result.team_window:4d} {result.prior_matches:5g} {_half_life_text(result):>5s}"
            f" {result.rho:7.2f}    {result.mean_log_loss:.5f}"
        )
    print(
        "Reference without team strengths (league averages): "
        f"{league_average_log_loss(matches):.5f}"
    )
    best = results[0]
    print(
        f"Best: N = {best.team_window}, m = {best.prior_matches:g}, "
        f"h = {_half_life_text(best)}, rho = {best.rho:g}"
    )
    return 0


def _half_life_text(result: CalibrationResult) -> str:
    return "-" if result.half_life is None else f"{result.half_life:g}"


def _warm_up_and_calibration(
    matches: Iterable[Match], warm_up_seasons: Sequence[str], calibration_seasons: Sequence[str]
) -> list[Match]:
    used_seasons = {*warm_up_seasons, *calibration_seasons}
    selected = [match for match in matches if match.season in used_seasons]
    if not any(match.season in calibration_seasons for match in selected):
        raise ValueError("there are no matches from the calibration seasons")
    return selected


if __name__ == "__main__":
    sys.exit(main(competition=sys.argv[1] if len(sys.argv) > 1 else COMPETITION))
