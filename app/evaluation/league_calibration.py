"""Calibrate all three outcome models of each league on that league's own seasons.

Run from the project folder with ``python -m app.evaluation.league_calibration`` (every
competition in the database) or name the competitions (``... E0 I1``). For each league, on the
warm-up season 2006/07 and the calibration seasons 2007/08-2009/10 only (the evaluation seasons
are never read):

1. Elo: the (K, H, goal margin) choice with the lowest mean squared error of the expected score;
2. Poisson: the (N, m, h, rho) choice with the lowest mean -ln P(actual score), N and h on the
   league's grids;
3. logistic regression: the (extra features, L2) choice with the lowest log loss, using the Elo
   of step 1 and, for the expected-goals difference, the Poisson model of step 2.

A best value on the edge of its grid is flagged, because the grid may then be too narrow (for h,
the longest half-life; for rho, the strongest correction). The last lines give the values for
``app/prediction/settings.py``.
"""

import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from app.data.competitions import competition as league_of
from app.data.models import Match
from app.data.paths import DATABASE_PATH
from app.data.repository import MatchRepository
from app.evaluation import elo_calibration, logistic_calibration, poisson_calibration
from app.prediction.logistic_predictions import MIN_TRAINING_MATCHES


@dataclass(frozen=True, slots=True)
class LeagueCalibration:
    """The best value of every hyperparameter of one league, with each model's reference."""

    competition: str
    elo: elo_calibration.CalibrationResult
    elo_reference: float  # constant prediction, no ratings
    poisson: poisson_calibration.CalibrationResult
    poisson_reference: float  # league averages, no team strengths
    logistic: logistic_calibration.CalibrationResult
    logistic_reference: float  # warm-up result frequencies
    edges: tuple[str, ...]  # hyperparameters whose best value lies on the edge of the grid


def calibrate_league(
    matches: Iterable[Match], *, min_training_matches: int = MIN_TRAINING_MATCHES
) -> LeagueCalibration:
    """Calibrate Elo, then Poisson, then logistic regression (with that Elo) for one league."""
    matches = list(matches)
    codes = {match.competition for match in matches}
    if len(codes) != 1:
        raise ValueError(f"matches must come from one competition, got {sorted(codes)}")
    league = league_of(codes.pop())
    elo = elo_calibration.calibrate(matches)[0]
    poisson = poisson_calibration.calibrate(matches)[0]
    logistic = logistic_calibration.calibrate(
        matches,
        elo=elo.settings,
        poisson=poisson.settings(league.season_length),
        min_training_matches=min_training_matches,
    )[0]
    grids = {
        "K": (elo.k_factor, elo_calibration.K_FACTORS),
        "H": (elo.home_advantage, elo_calibration.HOME_ADVANTAGES),
        "N": (poisson.team_window, poisson_calibration.team_windows(league.venue_season_length)),
        "m": (poisson.prior_matches, poisson_calibration.PRIOR_MATCHES),
        "L2": (logistic.l2, logistic_calibration.L2_VALUES),
    }
    edges = [name for name, (best, grid) in grids.items() if best in (min(grid), max(grid))]
    longest = max(h for h in poisson_calibration.half_lives(league.venue_season_length) if h)
    if poisson.half_life == longest:
        edges.append("h")
    if poisson.rho == min(poisson_calibration.RHO_VALUES):
        edges.append("rho")
    return LeagueCalibration(
        competition=league.code,
        elo=elo,
        elo_reference=elo_calibration.constant_prediction_error(matches),
        poisson=poisson,
        poisson_reference=poisson_calibration.league_average_log_loss(matches),
        logistic=logistic,
        logistic_reference=logistic_calibration.constant_frequency_log_loss(matches),
        edges=tuple(edges),
    )


def main(
    database_path: Path = DATABASE_PATH,
    competitions: Sequence[str] | None = None,
    *,
    min_training_matches: int = MIN_TRAINING_MATCHES,
) -> int:
    """Calibrate each competition (default: all in the database) and print the results."""
    if not database_path.is_file():
        print(
            f"Database not found: {database_path}\nRun: python -m app.data.build_database",
            file=sys.stderr,
        )
        return 1
    with MatchRepository.open(database_path) as repository:
        codes = list(competitions or repository.competitions())
        results = [
            calibrate_league(repository.matches(code), min_training_matches=min_training_matches)
            for code in codes
        ]
    print(
        "Calibration on each league's own seasons (warm-up 2006-07, calibration 2007-08 to 2009-10)"
    )
    print(
        f"{'league':6s} {'K':>4s} {'H':>4s} {'G':>3s} {'Elo MSE':>9s} {'(ref)':>9s}"
        f" {'N':>4s} {'m':>4s} {'h':>4s} {'rho':>5s} {'-ln P':>9s} {'(ref)':>9s}"
        f" {'L2':>6s} {'log loss':>9s} {'(ref)':>9s}  extra features; edge of grid"
    )
    for r in results:
        half_life = "-" if r.poisson.half_life is None else f"{r.poisson.half_life:g}"
        print(
            f"{r.competition:6s} {r.elo.k_factor:4g} {r.elo.home_advantage:4g}"
            f" {'yes' if r.elo.goal_margin else 'no':>3s}"
            f" {r.elo.mean_squared_error:9.5f} {r.elo_reference:9.5f}"
            f" {r.poisson.team_window:4d} {r.poisson.prior_matches:4g} {half_life:>4s}"
            f" {r.poisson.rho:5.2f} {r.poisson.mean_log_loss:9.5f} {r.poisson_reference:9.5f}"
            f" {r.logistic.l2:6g} {r.logistic.log_loss:9.5f} {r.logistic_reference:9.5f}"
            f"  {logistic_calibration.features_text(r.logistic)}; {', '.join(r.edges) or '-'}"
        )
    print("\nFor app/prediction/settings.py:")
    for r in results:
        print(f'    "{r.competition}": {settings_call(r)},')
    return 0


def settings_call(result: LeagueCalibration) -> str:
    """The ``league_settings`` call of a league's calibrated values, as settings.py writes it."""
    values = (
        result.elo.k_factor,
        result.elo.home_advantage,
        result.poisson.team_window,
        result.poisson.prior_matches,
        result.logistic.l2,
    )
    options = {
        "goal_margin": result.elo.goal_margin,
        "half_life": result.poisson.half_life,
        "rho": result.poisson.rho,
        "extra_features": result.logistic.extra_features,
    }
    defaults = {"goal_margin": False, "half_life": None, "rho": 0.0, "extra_features": ()}
    chosen = [f"{name}={value!r}" for name, value in options.items() if value != defaults[name]]
    arguments = [repr(result.competition), *(f"{value:g}" for value in values), *chosen]
    return f"league_settings({', '.join(arguments)})"


if __name__ == "__main__":
    sys.exit(main(competitions=sys.argv[1:] or None))
