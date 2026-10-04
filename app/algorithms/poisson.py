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


def score_distribution(
    home_expected_goals: float,
    away_expected_goals: float,
    max_goals: int = DEFAULT_MAX_GOALS,
) -> ScoreDistribution:
    """Build the score table of Eq. 2 for the two expected-goal values."""
    home = np.array(goal_probabilities(home_expected_goals, max_goals))
    away = np.array(goal_probabilities(away_expected_goals, max_goals))
    table = np.outer(home, away)
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
    )


def strength(goals: float, matches: int, league_average: float, prior_matches: float) -> float:
    """Eq. 4: goals per match relative to the league average, pulled towards 1 by m matches.

    For attack, ``goals`` are goals scored; for defensive weakness, goals conceded. With no
    matches the result is exactly 1, an average team.
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
