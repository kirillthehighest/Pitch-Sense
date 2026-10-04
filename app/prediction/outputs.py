"""The shared prediction format: every model's view of a match in the same shape.

Outcome probabilities are always ordered home win, draw, away win; they are non-negative and sum
to 1 within PROBABILITY_TOLERANCE. Expected goals and the score table exist only for the Poisson
model. K-Means does not predict matches and has no place here.
"""

import math
from dataclasses import dataclass
from enum import StrEnum

from app.algorithms.poisson import ScoreDistribution
from app.data.models import Outcome
from app.prediction.elo_predictions import EloOutcomePrediction
from app.prediction.logistic_predictions import LogisticPrediction
from app.prediction.poisson_predictions import PoissonPrediction

PROBABILITY_TOLERANCE = 1e-9


class ModelName(StrEnum):
    """The models that predict match outcomes."""

    ELO = "Elo"
    POISSON = "Poisson"
    LOGISTIC_REGRESSION = "Logistic regression"


@dataclass(frozen=True, slots=True)
class OutcomeProbabilities:
    """P(home win), P(draw), P(away win), checked to be a valid probability distribution."""

    home_win: float
    draw: float
    away_win: float

    def __post_init__(self) -> None:
        values = self.as_tuple()
        if not all(math.isfinite(value) and value >= 0 for value in values):
            raise ValueError(f"probabilities must be non-negative numbers, got {values}")
        if abs(math.fsum(values) - 1.0) > PROBABILITY_TOLERANCE:
            raise ValueError(f"probabilities must sum to 1, got {math.fsum(values)}")

    def as_tuple(self) -> tuple[float, float, float]:
        return self.home_win, self.draw, self.away_win

    def of(self, outcome: Outcome) -> float:
        """The probability of one outcome."""
        return {
            Outcome.HOME_WIN: self.home_win,
            Outcome.DRAW: self.draw,
            Outcome.AWAY_WIN: self.away_win,
        }[outcome]

    @property
    def most_likely(self) -> Outcome:
        """The outcome with the highest probability; ties go to home win, then draw."""
        outcomes = (Outcome.HOME_WIN, Outcome.DRAW, Outcome.AWAY_WIN)
        return max(outcomes, key=lambda outcome: (self.of(outcome), -outcomes.index(outcome)))


@dataclass(frozen=True, eq=False)
class ModelPrediction:
    """One model's prediction for one match, in the shared format."""

    model: ModelName
    probabilities: OutcomeProbabilities
    expected_goals: tuple[float, float] | None = None
    score_distribution: ScoreDistribution | None = None


def from_elo(prediction: EloOutcomePrediction) -> ModelPrediction:
    return ModelPrediction(
        model=ModelName.ELO, probabilities=OutcomeProbabilities(*prediction.probabilities)
    )


def from_poisson(prediction: PoissonPrediction) -> ModelPrediction:
    distribution = prediction.distribution
    return ModelPrediction(
        model=ModelName.POISSON,
        probabilities=OutcomeProbabilities(*distribution.outcome_probabilities()),
        expected_goals=(distribution.home_expected_goals, distribution.away_expected_goals),
        score_distribution=distribution,
    )


def from_logistic(prediction: LogisticPrediction) -> ModelPrediction:
    return ModelPrediction(
        model=ModelName.LOGISTIC_REGRESSION,
        probabilities=OutcomeProbabilities(*prediction.probabilities),
    )
