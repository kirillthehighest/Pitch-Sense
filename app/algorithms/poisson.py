"""Poisson model of football scores, implemented from its definition.

Notation, as in docs/algorithms/poisson.md:

    lambda_h, lambda_a   expected goals of the home and away team
    P(k; lambda)         probability of exactly k goals                                 (Eq. 1)
                         lambda^k e^(-lambda) / k!, computed as
                         P(0) = e^(-lambda) and P(k) = P(k - 1) * lambda / k
    P(i, j)              probability of the score i-j, the home and away goals being    (Eq. 2)
                         independent: P(i; lambda_h) * P(j; lambda_a)
    P(H), P(D), P(A)     sums of P(i, j) over i > j, i = j and i < j                    (Eq. 3)
    strength             goals per match relative to the league average mu, pulled      (Eq. 4)
                         towards 1 (an average team) by m imaginary average matches:
                         ((goals + m * mu) / (matches + m)) / mu
    lambda               attack strength * opponent's defensive weakness * mu           (Eq. 5)
    tau(i, j)            Dixon-Coles correction of the four low scores, with rho <= 0    (Eq. 6)
                         adding to 0-0 and 1-1 what it takes from 1-0 and 0-1:
                         tau(0,0) = 1 - lambda_h lambda_a rho,  tau(0,1) = 1 + lambda_h rho,
                         tau(1,0) = 1 + lambda_a rho,  tau(1,1) = 1 - rho,  else 1;
                         P(i, j) becomes tau(i, j) P(i, j)
    w_j                  weight of a team's j-th most recent match (j = 0 the latest)    (Eq. 7)
                         with half-life h: 2^(-j / h); goals and matches in Eq. 4 are then
                         the weighted sums, and without h every match weighs 1

The independence of Eq. 2 under-predicts draws, mostly 0-0 and 1-1 (Dixon and Coles, 1997);
tau moves probability between the four low scores only. It keeps the total and both teams'
expected goals unchanged, because the four changes cancel out:
e^(-lambda_h - lambda_a) * lambda_h lambda_a rho * (-1 + 1 + 1 - 1) = 0. Dixon and Coles only
require every tau to be non-negative, but rho here is one value for a whole league: in a very
uneven match (lambda = 5, rho = -0.2) that limit would make a 0-1 impossible. So no tau may fall
below 1/2, which limits rho to
    [-1 / (2 max(lambda_h, lambda_a)),  min(1, 1 / (lambda_h lambda_a)) / 2];
in usual matches (both lambdas at most 2.5) a rho down to -0.2 applies in full.

Scores are kept up to ``max_goals`` for each side. The small probability of higher scores is
reported as ``truncated_mass`` and the kept probabilities are rescaled to sum to 1.
"""

import math
from dataclasses import dataclass

import numpy as np

# Above 20 goals a side loses less than 2e-6 of its probability even at lambda = 6; the largest
# lambda on the real data is about 4.9 (a cut-off at 10 goals would lose 1.2% there).
DEFAULT_MAX_GOALS = 20
MAX_TRUNCATED_MASS = 0.01  # refuse to drop more than 1% of the probability
MIN_LOW_SCORE_FACTOR = 0.5  # the smallest tau of Eq. 6: no low score loses more than half


def goal_probabilities(expected_goals: float, max_goals: int) -> list[float]:
    """Eq. 1: P(k; lambda) for k = 0 .. max_goals.

    The recurrence P(k) = P(k - 1) * lambda / k avoids computing lambda^k and k! separately,
    which would overflow for large k.
    """
    _check_expected_goals(expected_goals)
    if max_goals < 0:
        raise ValueError(f"max_goals cannot be negative, got {max_goals}")
    probabilities = [math.exp(-expected_goals)]
    for goals in range(1, max_goals + 1):
        probabilities.append(probabilities[-1] * expected_goals / goals)
    return probabilities


@dataclass(frozen=True, eq=False)
class ScoreDistribution:
    """Probabilities of every score up to ``max_goals`` for each side (Eq. 2).

    ``probabilities[i, j]`` is the probability that the home team scores i and the away team j.
    The array is read-only and sums to 1.
    """

    home_expected_goals: float
    away_expected_goals: float
    probabilities: np.ndarray
    truncated_mass: float
    rho: float = 0.0  # the Dixon-Coles rho applied (Eq. 6), after the limits

    def outcome_probabilities(self) -> tuple[float, float, float]:
        """Eq. 3: (P(H), P(D), P(A)), always in this order; they sum to 1."""
        home_win = np.tril(self.probabilities, k=-1).sum()  # below the diagonal: i > j
        draw = np.trace(self.probabilities)
        away_win = np.triu(self.probabilities, k=1).sum()  # above the diagonal: i < j
        return float(home_win), float(draw), float(away_win)

    def most_likely_scores(self, count: int = 5) -> list[tuple[int, int, float]]:
        """Return the ``count`` most likely scores as (home goals, away goals, probability)."""
        if count < 1:
            raise ValueError(f"count must be at least 1, got {count}")
        cells = [
            (int(home_goals), int(away_goals), float(probability))
            for (home_goals, away_goals), probability in np.ndenumerate(self.probabilities)
        ]
        cells.sort(key=lambda cell: (-cell[2], cell[0], cell[1]))
        return cells[:count]


def admissible_rho(home_expected_goals: float, away_expected_goals: float, rho: float) -> float:
    """``rho`` limited so that no tau of Eq. 6 falls below MIN_LOW_SCORE_FACTOR for these
    expected goals."""
    _check_expected_goals(home_expected_goals)
    _check_expected_goals(away_expected_goals)
    if not math.isfinite(rho):
        raise ValueError(f"rho must be a finite number, got {rho}")
    room = 1.0 - MIN_LOW_SCORE_FACTOR
    largest = max(home_expected_goals, away_expected_goals)
    lower = -room / largest if largest > 0 else -math.inf  # tau(0, 1), tau(1, 0)
    product_goals = home_expected_goals * away_expected_goals
    upper = room * min(1.0, 1.0 / product_goals) if product_goals > 0 else room  # tau(0,0), (1,1)
    return min(max(rho, lower), upper)


def low_score_correction(
    home_expected_goals: float, away_expected_goals: float, rho: float
) -> np.ndarray:
    """Eq. 6: the 2 x 2 table tau(i, j) for i, j in {0, 1}; ``rho`` must be admissible."""
    home, away = home_expected_goals, away_expected_goals
    return np.array([[1.0 - home * away * rho, 1.0 + home * rho], [1.0 + away * rho, 1.0 - rho]])


def score_distribution(
    home_expected_goals: float,
    away_expected_goals: float,
    max_goals: int = DEFAULT_MAX_GOALS,
    rho: float = 0.0,
) -> ScoreDistribution:
    """Build the score table of Eq. 2 for the two expected-goal values, with the Dixon-Coles
    correction of Eq. 6 when ``rho`` is not 0 (limited by ``admissible_rho``)."""
    home = np.array(goal_probabilities(home_expected_goals, max_goals))
    away = np.array(goal_probabilities(away_expected_goals, max_goals))
    table = np.outer(home, away)
    rho = admissible_rho(home_expected_goals, away_expected_goals, rho)
    if rho and max_goals >= 1:
        table[:2, :2] *= low_score_correction(home_expected_goals, away_expected_goals, rho)
    kept = float(table.sum())
    truncated_mass = 1.0 - kept
    if truncated_mass > MAX_TRUNCATED_MASS:
        raise ValueError(
            f"scores above {max_goals} goals hold {truncated_mass:.2%} of the probability; "
            "increase max_goals"
        )
    table /= kept
    table.setflags(write=False)
    return ScoreDistribution(
        home_expected_goals=home_expected_goals,
        away_expected_goals=away_expected_goals,
        probabilities=table,
        truncated_mass=max(truncated_mass, 0.0),
        rho=rho,
    )


def recency_weights(count: int, half_life: float | None) -> list[float]:
    """Eq. 7: the weights of a team's last ``count`` matches, oldest first; the most recent
    weighs 1 and each step back multiplies the weight by 2^(-1 / h). Without a half-life every
    match weighs 1."""
    if count < 0:
        raise ValueError(f"count cannot be negative, got {count}")
    if half_life is None:
        return [1.0] * count
    if not (math.isfinite(half_life) and half_life > 0):
        raise ValueError(f"half_life must be a positive number, got {half_life}")
    return [2.0 ** (-(count - 1 - position) / half_life) for position in range(count)]


def strength(goals: float, matches: float, league_average: float, prior_matches: float) -> float:
    """Eq. 4: goals per match relative to the league average, pulled towards 1 by m matches.

    For attack, ``goals`` are goals scored; for defensive weakness, goals conceded. Weighted
    matches (Eq. 7) give weighted sums of goals and matches. With no matches the result is
    exactly 1, an average team.
    """
    if goals < 0 or matches < 0:
        raise ValueError(f"goals and matches cannot be negative, got {goals} and {matches}")
    if not (math.isfinite(league_average) and league_average > 0):
        raise ValueError(f"league_average must be a positive number, got {league_average}")
    if not (math.isfinite(prior_matches) and prior_matches >= 0):
        raise ValueError(f"prior_matches must be zero or positive, got {prior_matches}")
    if matches + prior_matches == 0:
        raise ValueError("need at least one match or a positive prior_matches")
    return (goals + prior_matches * league_average) / (matches + prior_matches) / league_average


def expected_goals(attack_strength: float, defence_weakness: float, league_average: float) -> float:
    """Eq. 5: lambda = attack strength * opponent's defensive weakness * league average goals.

    ``defence_weakness`` is how many goals the opponent concedes relative to the league average:
    1 is average, above 1 a weaker defence.
    """
    for name, value in (
        ("attack_strength", attack_strength),
        ("defence_weakness", defence_weakness),
        ("league_average", league_average),
    ):
        if not (math.isfinite(value) and value >= 0):
            raise ValueError(f"{name} must be zero or positive, got {value}")
    return attack_strength * defence_weakness * league_average


def _check_expected_goals(value: float) -> None:
    if not (math.isfinite(value) and value >= 0):
        raise ValueError(f"expected goals must be zero or positive, got {value}")
