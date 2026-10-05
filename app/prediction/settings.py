"""The hyperparameters of the three outcome models, one set per competition.

Every league is calibrated on its own seasons: warm-up 2006/07 and calibration 2007/08-2009/10
(``app/evaluation/periods.py``), with ``python -m app.evaluation.league_calibration``; the
evaluation seasons never influence these values. Windows of "one season" follow the league's
usual size (``app/data/competitions.py``): 380 matches and 19 home matches per team in a
20-team league, 306 and 17 in an 18-team league.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.data.competitions import competition
from app.data.models import Match


@dataclass(frozen=True, slots=True)
class EloSettings:
    """K, the rating change per unit of surprise, and H, the home advantage in rating points."""

    k_factor: float
    home_advantage: float


@dataclass(frozen=True, slots=True)
class PoissonSettings:
    """N, the venue matches behind a team's strengths; m, the prior weight in matches; and the
    number of league matches behind the league averages."""

    team_window: int
    prior_matches: float
    league_window: int


@dataclass(frozen=True, slots=True)
class LogisticSettings:
    """The L2 strength, the Elo run behind the Elo-difference feature, and the feature windows:
    a team's home (or away) matches of one season and the league matches of one season."""

    l2: float
    elo: EloSettings
    venue_window: int
    league_window: int


@dataclass(frozen=True, slots=True)
class ModelSettings:
    """Everything the three outcome models of one competition need."""

    elo: EloSettings
    poisson: PoissonSettings
    logistic: LogisticSettings


def league_settings(
    code: str,
    k_factor: float,
    home_advantage: float,
    team_window: int,
    prior_matches: float,
    l2: float,
) -> ModelSettings:
    """Combine calibrated values with the windows of one season of the competition."""
    league = competition(code)
    elo = EloSettings(k_factor, home_advantage)
    return ModelSettings(
        elo=elo,
        poisson=PoissonSettings(team_window, prior_matches, league.season_length),
        logistic=LogisticSettings(l2, elo, league.venue_season_length, league.season_length),
    )


# (K, H, N, m, L2) chosen by `python -m app.evaluation.league_calibration` on each league's own
# warm-up and calibration seasons (run of 2026-10-05); see docs/leagues.md. La Liga's N moved
# from 38 to 76 when the N grid was extended to five seasons for every league (Phase 15).
_CALIBRATED: Mapping[str, tuple[float, float, int, float, float]] = {
    "E0": (25, 80, 76, 10, 0.01),
    "SP1": (15, 80, 76, 20, 0.1),
    "I1": (20, 100, 38, 20, 0.1),
    "D1": (15, 60, 51, 20, 0.1),
    "F1": (15, 60, 38, 30, 0.1),
}
SETTINGS: Mapping[str, ModelSettings] = {
    code: league_settings(code, *values) for code, values in _CALIBRATED.items()
}


def settings_for(code: str) -> ModelSettings:
    """The calibrated settings of a competition; a league without them is an error."""
    try:
        return SETTINGS[code]
    except KeyError:
        raise ValueError(
            f"competition {code!r} has no calibrated settings; run "
            "python -m app.evaluation.league_calibration and add them to app/prediction/settings.py"
        ) from None


def settings_of(matches: Iterable[Match]) -> ModelSettings:
    """The settings of the one competition the matches belong to."""
    codes = {match.competition for match in matches}
    if len(codes) != 1:
        raise ValueError(f"matches must come from one competition, got {sorted(codes)}")
    return settings_for(codes.pop())
