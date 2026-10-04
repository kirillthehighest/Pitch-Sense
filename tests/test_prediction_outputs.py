import math
from datetime import date

import pytest

from app.algorithms.poisson import score_distribution
from app.data.models import Match, Outcome
from app.prediction.elo_predictions import EloOutcomePrediction, EloPrediction
from app.prediction.logistic_predictions import LogisticPrediction
from app.prediction.outputs import (
    ModelName,
    OutcomeProbabilities,
    from_elo,
    from_logistic,
    from_poisson,
)
from app.prediction.poisson_predictions import PoissonPrediction

MATCH = Match(
    competition="SP1",
    season="2006-07",
    match_date=date(2006, 9, 1),
    home_team="Alpha",
    away_team="Bravo",
    home_goals=1,
    away_goals=0,
    result=Outcome.HOME_WIN,
)


def test_valid_probabilities():
    probabilities = OutcomeProbabilities(0.5, 0.3, 0.2)

    assert probabilities.as_tuple() == (0.5, 0.3, 0.2)
    assert probabilities.of(Outcome.DRAW) == 0.3
    assert probabilities.of(Outcome.AWAY_WIN) == 0.2


def test_tiny_rounding_errors_are_accepted():
    OutcomeProbabilities(0.5, 0.3, 0.2 + 5e-10)


@pytest.mark.parametrize(
    "values", [(0.5, 0.3, 0.3), (0.5, 0.6, -0.1), (math.nan, 0.5, 0.5), (0.5, 0.5, math.inf)]
)
def test_invalid_probabilities_are_rejected(values):
    with pytest.raises(ValueError):
        OutcomeProbabilities(*values)


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((0.5, 0.3, 0.2), Outcome.HOME_WIN),
        ((0.2, 0.3, 0.5), Outcome.AWAY_WIN),
        ((0.4, 0.4, 0.2), Outcome.HOME_WIN),
        ((0.2, 0.4, 0.4), Outcome.DRAW),
    ],
)
def test_most_likely_outcome_with_ties_going_home_then_draw(values, expected):
    assert OutcomeProbabilities(*values).most_likely is expected


def test_from_poisson_keeps_expected_goals_and_the_score_table():
    distribution = score_distribution(1.0, 0.0)
    prediction = PoissonPrediction(
        match=MATCH,
        league_home_goals=1.5,
        league_away_goals=1.1,
        home_attack=1.0,
        home_defence_weakness=1.0,
        away_attack=1.0,
        away_defence_weakness=1.0,
        distribution=distribution,
    )

    converted = from_poisson(prediction)

    assert converted.model is ModelName.POISSON
    assert converted.probabilities.as_tuple() == pytest.approx(
        (1 - math.exp(-1), math.exp(-1), 0.0), abs=1e-7
    )
    assert converted.expected_goals == (1.0, 0.0)
    assert converted.score_distribution is distribution


def test_from_logistic():
    prediction = LogisticPrediction(
        match=MATCH,
        features=(0.0,) * 5,
        probabilities=(0.5, 0.25, 0.25),
        training_matches=100,
        training_iterations=10,
        training_converged=True,
    )

    converted = from_logistic(prediction)

    assert converted.model is ModelName.LOGISTIC_REGRESSION
    assert converted.probabilities.as_tuple() == (0.5, 0.25, 0.25)
    assert converted.expected_goals is None
    assert converted.score_distribution is None


def test_from_elo():
    prediction = EloOutcomePrediction(
        prediction=EloPrediction(MATCH, 1510.0, 1490.0, 0.64),
        probabilities=(0.515, 0.25, 0.235),
        draw_model_matches=200,
    )

    converted = from_elo(prediction)

    assert converted.model is ModelName.ELO
    assert converted.probabilities.as_tuple() == (0.515, 0.25, 0.235)


def test_converters_refuse_invalid_probabilities():
    prediction = LogisticPrediction(
        match=MATCH,
        features=(0.0,) * 5,
        probabilities=(0.5, 0.2, 0.2),
        training_matches=100,
        training_iterations=10,
        training_converged=True,
    )

    with pytest.raises(ValueError, match="sum to 1"):
        from_logistic(prediction)
