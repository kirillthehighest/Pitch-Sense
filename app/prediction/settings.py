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
    """K, the rating change per unit of surprise; H, the home advantage in rating points; and
    whether the goal margin weights each update (Phase 23)."""

    k_factor: float
    home_advantage: float
    goal_margin: bool = False


@dataclass(frozen=True, slots=True)
class PoissonSettings:
    """N, the venue matches behind a team's strengths; m, the prior weight in matches; the
    number of league matches behind the league averages; and (Phase 23) h, the half-life in
    matches of the recency weights (None: equal weights), and rho of the Dixon-Coles
    correction (0: none)."""

    team_window: int
    prior_matches: float
    league_window: int
    half_life: float | None = None
    rho: float = 0.0


@dataclass(frozen=True, slots=True)
class LogisticSettings:
    """The L2 strength, the Elo run behind the Elo-difference feature, and the feature windows:
    a team's home (or away) matches of one season and the league matches of one season. Since
    Phase 23 the calibration may add features to the five (``extra_features``, names from
    ``app/prediction/logistic_features.py``); the expected-goals difference needs the Poisson
    run behind it (``poisson``)."""

    l2: float
    elo: EloSettings
    venue_window: int
    league_window: int
    extra_features: tuple[str, ...] = ()
    poisson: PoissonSettings | None = None


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
    *,
    goal_margin: bool = False,
    half_life: float | None = None,
    rho: float = 0.0,
    extra_features: tuple[str, ...] = (),
) -> ModelSettings:
    """Combine calibrated values with the windows of one season of the competition."""
    league = competition(code)
    elo = EloSettings(k_factor, home_advantage, goal_margin)
    poisson = PoissonSettings(team_window, prior_matches, league.season_length, half_life, rho)
    return ModelSettings(
        elo=elo,
        poisson=poisson,
        logistic=LogisticSettings(
            l2,
            elo,
            league.venue_season_length,
            league.season_length,
            extra_features,
            poisson,
        ),
    )


# Chosen by `python -m app.evaluation.league_calibration` on each league's own warm-up and
# calibration seasons; see docs/leagues.md. Phase 15 chose (K, H, N, m, L2) on 2026-10-05. Phase 23
# (run of 2026-10-16) added the goal margin of Elo, the half-life and rho of Poisson and the
# extra features of logistic regression to the grids, with K = 5 and a four-season half-life
# after the first run chose the edges, and recalibrated every value.
_EXPECTED_GOALS = ("expected_goals_difference",)
SETTINGS: Mapping[str, ModelSettings] = {
    "E0": league_settings(
        "E0", 15, 80, 76, 5, 0.1, goal_margin=True, half_life=19, rho=-0.08,
        extra_features=_EXPECTED_GOALS,
    ),
    "SP1": league_settings(
        "SP1", 10, 80, 76, 10, 0.1, goal_margin=True, half_life=19, rho=-0.04,
        extra_features=("elo_gap", *_EXPECTED_GOALS),
    ),
    "I1": league_settings("I1", 20, 100, 38, 20, 0.1, rho=-0.06, extra_features=_EXPECTED_GOALS),
    "D1": league_settings("D1", 10, 60, 68, 10, 0.1, goal_margin=True, half_life=34, rho=-0.06),
    "F1": league_settings("F1", 15, 60, 57, 20, 0.1, half_life=19, rho=-0.1),
}  # fmt: skip


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
