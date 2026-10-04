import math

import numpy as np
import pytest

from app.algorithms.poisson import (
    expected_goals,
    goal_probabilities,
    score_distribution,
    strength,
)

# --- Eq. 1: probability of k goals ---


def test_goal_probabilities_for_one_expected_goal():
    probabilities = goal_probabilities(1.0, max_goals=3)

    assert probabilities == pytest.approx(
        [math.exp(-1), math.exp(-1), math.exp(-1) / 2, math.exp(-1) / 6]
    )
    assert probabilities[0] == pytest.approx(0.367879, abs=1e-6)


def test_goal_probabilities_hand_value():
    # P(3; 2.5) = 2.5^3 e^(-2.5) / 3! = 15.625 * 0.082085 / 6
    assert goal_probabilities(2.5, max_goals=3)[3] == pytest.approx(0.213763, abs=1e-6)


def test_zero_expected_goals_means_certainly_zero_goals():
    assert goal_probabilities(0.0, max_goals=3) == [1.0, 0.0, 0.0, 0.0]


def test_recurrence_matches_the_closed_formula():
    expected = 3.7
    probabilities = goal_probabilities(expected, max_goals=20)

    for goals, probability in enumerate(probabilities):
        closed_formula = expected**goals * math.exp(-expected) / math.factorial(goals)
        assert probability == pytest.approx(closed_formula, rel=1e-12)


@pytest.mark.parametrize("expected", [0.3, 1.4, 2.9, 50.0])
def test_probabilities_sum_to_one_and_average_lambda(expected):
    probabilities = goal_probabilities(expected, max_goals=200)

    assert math.fsum(probabilities) == pytest.approx(1, abs=1e-12)
    mean = math.fsum(goals * p for goals, p in enumerate(probabilities))
    assert mean == pytest.approx(expected, rel=1e-9)


@pytest.mark.parametrize(("expected", "max_goals"), [(-0.5, 5), (math.nan, 5), (1.0, -1)])
def test_invalid_goal_probability_arguments(expected, max_goals):
    with pytest.raises(ValueError):
        goal_probabilities(expected, max_goals)


# --- Eq. 2: score table ---


def test_each_score_is_the_product_of_both_sides_probabilities():
    distribution = score_distribution(1.4, 0.9, max_goals=10)
    home = goal_probabilities(1.4, 10)
    away = goal_probabilities(0.9, 10)
    kept = math.fsum(home) * math.fsum(away)

    assert distribution.probabilities[2, 1] == pytest.approx(home[2] * away[1] / kept)
    assert distribution.probabilities[0, 0] == pytest.approx(math.exp(-2.3) / kept)


def test_table_sums_to_one_and_reports_the_truncated_mass():
    distribution = score_distribution(1.0, 0.8, max_goals=4)
    kept = math.fsum(goal_probabilities(1.0, 4)) * math.fsum(goal_probabilities(0.8, 4))

    assert distribution.probabilities.sum() == pytest.approx(1, abs=1e-12)
    assert distribution.truncated_mass == pytest.approx(1 - kept)
    assert distribution.truncated_mass > 0


def test_too_much_truncated_probability_is_refused():
    with pytest.raises(ValueError, match="increase max_goals"):
        score_distribution(8.0, 1.0, max_goals=2)


def test_table_is_read_only():
    distribution = score_distribution(1.2, 1.1)

    with pytest.raises(ValueError):
        distribution.probabilities[0, 0] = 1.0


def test_swapping_the_teams_transposes_the_table():
    forward = score_distribution(1.7, 0.8)
    backward = score_distribution(0.8, 1.7)

    np.testing.assert_allclose(forward.probabilities, backward.probabilities.T)


# --- Eq. 3: home, draw and away probabilities ---


def test_outcome_probabilities_hand_example():
    # The away team never scores, so the home team wins whenever it scores at least once.
    home_win, draw, away_win = score_distribution(1.0, 0.0).outcome_probabilities()

    assert home_win == pytest.approx(1 - math.exp(-1), abs=1e-7)
    assert draw == pytest.approx(math.exp(-1), abs=1e-7)
    assert away_win == 0.0


def test_no_expected_goals_means_a_certain_goalless_draw():
    assert score_distribution(0.0, 0.0).outcome_probabilities() == (0.0, 1.0, 0.0)


@pytest.mark.parametrize(("home", "away"), [(1.5, 1.5), (2.1, 0.7), (0.6, 1.9), (0.0, 2.5)])
def test_outcome_probabilities_are_valid(home, away):
    probabilities = score_distribution(home, away).outcome_probabilities()

    assert min(probabilities) >= 0
    assert sum(probabilities) == pytest.approx(1, abs=1e-12)


def test_equal_expected_goals_give_equal_win_chances():
    home_win, _, away_win = score_distribution(1.3, 1.3).outcome_probabilities()

    assert home_win == pytest.approx(away_win, abs=1e-12)


def test_more_expected_goals_mean_a_higher_win_chance():
    weaker = score_distribution(1.2, 1.0).outcome_probabilities()
    stronger = score_distribution(1.8, 1.0).outcome_probabilities()

    assert stronger[0] > weaker[0]
    assert stronger[2] < weaker[2]


def test_most_likely_scores():
    # P(1-0) = 0.3230 * 0.4066, P(1-1) = 0.3230 * 0.3659, P(2-0) = 0.2584 * 0.4066
    scores = score_distribution(1.6, 0.9).most_likely_scores(3)

    assert [(home, away) for home, away, _ in scores] == [(1, 0), (1, 1), (2, 0)]
    assert scores[0][2] == pytest.approx(0.1313, abs=1e-4)
    assert [p for _, _, p in scores] == sorted((p for _, _, p in scores), reverse=True)


def test_most_likely_scores_needs_a_positive_count():
    with pytest.raises(ValueError):
        score_distribution(1.0, 1.0).most_likely_scores(0)


# --- Eq. 4 and 5: strengths and expected goals ---


def test_strength_relative_to_the_league_average():
    # 30 home goals in 19 home matches against a league average of 1.5 per match.
    assert strength(30, 19, league_average=1.5, prior_matches=0) == pytest.approx(30 / 19 / 1.5)
    # Five imaginary average matches: (30 + 5 * 1.5) / (19 + 5) / 1.5
    assert strength(30, 19, league_average=1.5, prior_matches=5) == pytest.approx(37.5 / 24 / 1.5)


def test_a_team_without_matches_is_average():
    assert strength(0, 0, league_average=1.5, prior_matches=5) == 1.0


def test_expected_goals_hand_example():
    assert expected_goals(1.2, 0.9, league_average=1.5) == pytest.approx(1.62)


@pytest.mark.parametrize(
    ("goals", "matches", "league_average", "prior_matches"),
    [(-1, 5, 1.5, 0), (3, -1, 1.5, 0), (3, 5, 0.0, 0), (3, 5, 1.5, -1), (0, 0, 1.5, 0)],
)
def test_invalid_strength_arguments(goals, matches, league_average, prior_matches):
    with pytest.raises(ValueError):
        strength(goals, matches, league_average, prior_matches)


@pytest.mark.parametrize("arguments", [(-0.1, 1.0, 1.5), (1.0, math.nan, 1.5), (1.0, 1.0, -2)])
def test_invalid_expected_goals_arguments(arguments):
    with pytest.raises(ValueError):
        expected_goals(*arguments)
