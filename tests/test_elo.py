import math
import random
from datetime import date, timedelta

import pytest

from app.algorithms.elo import (
    DrawModel,
    EloRatings,
    GameResult,
    actual_score,
    expected_score,
    margin_weight,
    rating_change,
)

FIRST_DAY = date(2006, 9, 1)


def game(day: int, home_team: str, away_team: str, home_goals: int, away_goals: int) -> GameResult:
    return GameResult(FIRST_DAY + timedelta(days=day), home_team, away_team, home_goals, away_goals)


def new_league(
    k_factor: float = 20, home_advantage: float = 0, teams=("A", "B", "C", "D"), goal_margin=False
):
    elo = EloRatings(k_factor=k_factor, home_advantage=home_advantage, goal_margin=goal_margin)
    elo.start_season(teams)
    return elo


# --- the three formulas ---


def test_expected_score_examples():
    assert expected_score(1500, 1500, home_advantage=0) == 0.5
    assert expected_score(1500, 1500, home_advantage=100) == pytest.approx(0.640065, abs=1e-6)
    assert expected_score(1900, 1500, home_advantage=0) == pytest.approx(10 / 11)


@pytest.mark.parametrize(("first", "second"), [(1500, 1500), (1620, 1480), (1350, 1710)])
def test_expected_scores_of_both_sides_sum_to_one_without_home_advantage(first, second):
    assert expected_score(first, second, 0) + expected_score(second, first, 0) == pytest.approx(1)


def test_actual_score_from_the_home_side():
    assert actual_score(2, 1) == 1.0
    assert actual_score(1, 1) == 0.5
    assert actual_score(0, 3) == 0.0
    with pytest.raises(ValueError):
        actual_score(-1, 0)


def test_rating_change_is_k_times_the_surprise():
    assert rating_change(expected=0.5, actual=1.0, k_factor=20) == 10
    assert rating_change(expected=0.5, actual=0.5, k_factor=20) == 0
    assert rating_change(expected=0.75, actual=0.0, k_factor=40) == -30
    assert rating_change(expected=0.5, actual=1.0, k_factor=20, weight=1.5) == 15


@pytest.mark.parametrize(
    ("home_goals", "away_goals", "weight"),
    [
        (0, 0, 1),
        (1, 0, 1),
        (0, 1, 1),
        (2, 0, 1.5),
        (1, 3, 1.5),
        (3, 0, 1.75),
        (0, 4, 1.875),
        (7, 0, 2.25),
    ],
)
def test_margin_weight_by_the_goal_margin(home_goals, away_goals, weight):
    assert margin_weight(home_goals, away_goals) == weight


def test_margin_weight_rejects_negative_goals():
    with pytest.raises(ValueError, match="negative"):
        margin_weight(-1, 0)


# --- updates ---


def test_equal_teams_without_home_advantage_exchange_half_of_k():
    elo = new_league()

    delta = elo.update(game(0, "A", "B", 2, 0))

    assert delta == 10
    assert (elo.rating("A"), elo.rating("B")) == (1510, 1490)


def test_home_win_with_home_advantage_gains_less():
    elo = new_league(home_advantage=100)

    delta = elo.update(game(0, "A", "B", 1, 0))

    assert delta == pytest.approx(20 * (1 - 0.640065), abs=1e-4)  # 7.1987
    assert elo.rating("A") == pytest.approx(1507.1987, abs=1e-4)


def test_home_draw_with_home_advantage_loses_points():
    elo = new_league(home_advantage=100)

    delta = elo.update(game(0, "A", "B", 1, 1))

    assert delta == pytest.approx(20 * (0.5 - 0.640065), abs=1e-4)  # -2.8013
    assert elo.rating("B") == pytest.approx(1502.8013, abs=1e-4)


def test_ratings_after_two_matches():
    elo = new_league()
    elo.update(game(0, "A", "B", 1, 0))  # A 1510, B 1490
    expected_for_b = elo.expected_home_score("B", "C")  # 1 / (1 + 10^(10/400)) = 0.485613

    elo.update(game(7, "B", "C", 3, 1))

    assert expected_for_b == pytest.approx(0.485613, abs=1e-6)
    assert elo.rating("B") == pytest.approx(1500.2877, abs=1e-3)
    assert elo.rating("C") == pytest.approx(1489.7123, abs=1e-3)
    assert (elo.rating("A"), elo.rating("D")) == (1510, 1500)


def test_a_wide_win_moves_more_points_only_with_the_goal_margin():
    plain = new_league()
    weighted = new_league(goal_margin=True)

    assert plain.update(game(0, "A", "B", 4, 0)) == 10
    assert weighted.update(game(0, "A", "B", 4, 0)) == 10 * 15 / 8  # G = (11 + 4) / 8
    assert weighted.update(game(1, "C", "D", 1, 0)) == 10  # a one-goal win keeps G = 1
    assert weighted.update(game(2, "B", "C", 2, 2)) == pytest.approx(
        20 * (0.5 - expected_score(1481.25, 1510, 0))
    )  # a draw is weighted 1: no margin


@pytest.mark.parametrize("goal_margin", [False, True])
def test_total_rating_never_changes(goal_margin):
    generator = random.Random(2006)
    teams = ("A", "B", "C", "D")
    elo = new_league(k_factor=32, home_advantage=60, teams=teams, goal_margin=goal_margin)

    for day in range(200):
        home_team, away_team = generator.sample(teams, 2)
        elo.update(
            game(day, home_team, away_team, generator.randint(0, 4), generator.randint(0, 4))
        )

    assert math.fsum(elo.ratings.values()) == pytest.approx(4 * 1500, abs=1e-9)


def test_all_draws_between_equal_teams_change_no_rating():
    elo = new_league()

    for day, (home_team, away_team) in enumerate([("A", "B"), ("C", "D"), ("B", "A"), ("D", "C")]):
        elo.update(game(day, home_team, away_team, 1, 1))

    assert set(elo.ratings.values()) == {1500}


def test_a_draw_model_fitted_on_draws_only_still_leaves_each_win_one_percent():
    model = DrawModel.fit([0.3, 0.5, 0.5, 0.7], [0.5] * 4)

    assert set(model.draw_rates) == {1.0}
    assert model.outcome_probabilities(0.5) == pytest.approx((0.01, 0.98, 0.01))
    assert model.outcome_probabilities(0.7) == pytest.approx(
        (0.41, 0.58, 0.01)
    )  # cap 2 * 0.3 - 0.02


def test_matches_must_be_chronological():
    elo = new_league()
    elo.update(game(10, "A", "B", 1, 0))
    elo.update(game(10, "C", "D", 0, 0))  # same day is allowed

    with pytest.raises(ValueError, match="chronological"):
        elo.update(game(9, "A", "C", 1, 0))


def test_teams_must_be_in_the_league():
    elo = new_league()

    with pytest.raises(ValueError, match="not in the league"):
        elo.update(game(0, "A", "Zulu", 1, 0))
    with pytest.raises(ValueError, match="not in the league"):
        EloRatings(k_factor=20, home_advantage=0).rating("A")


# --- seasons ---


def test_first_season_starts_every_team_at_the_initial_rating():
    elo = EloRatings(k_factor=20, home_advantage=50, initial_rating=1000)

    elo.start_season(["A", "B", "C"])

    assert elo.ratings == {"A": 1000, "B": 1000, "C": 1000}


def test_joining_teams_take_the_average_rating_of_the_teams_that_left():
    elo = new_league()
    elo.update(game(0, "A", "D", 1, 0))  # A 1510, D 1490
    elo.update(game(0, "C", "B", 1, 0))  # C 1510, B 1490
    total_before = math.fsum(elo.ratings.values())

    elo.start_season(["A", "B", "E", "F"])  # C (1510) and D (1490) leave

    assert elo.rating("E") == elo.rating("F") == 1500
    assert (elo.rating("A"), elo.rating("B")) == (1510, 1490)  # carried over unchanged
    assert math.fsum(elo.ratings.values()) == pytest.approx(total_before)


def test_a_returning_team_does_not_get_its_old_rating_back():
    elo = new_league()
    elo.update(game(0, "C", "D", 1, 0))  # C 1510 when it leaves
    elo.start_season(["A", "B", "D", "E"])  # C leaves, E joins at 1510
    elo.update(game(400, "A", "E", 1, 0))  # E drops to about 1499.71
    leaving_rating = elo.rating("E")

    elo.start_season(["A", "B", "D", "C"])  # E leaves, C returns

    assert elo.rating("C") == pytest.approx(leaving_rating)
    assert "E" not in elo.ratings


def test_league_expansion_starts_new_teams_at_the_league_average():
    elo = new_league(teams=("A", "B"))
    elo.update(game(0, "A", "B", 1, 0))

    elo.start_season(["A", "B", "C"])

    assert elo.rating("C") == 1500


@pytest.mark.parametrize("teams", [["A"], ["A", ""]])
def test_season_needs_two_named_teams(teams):
    with pytest.raises(ValueError, match="at least two teams"):
        EloRatings(k_factor=20, home_advantage=0).start_season(teams)


# --- validation ---


@pytest.mark.parametrize(
    "parameters",
    [
        {"k_factor": 0, "home_advantage": 0},
        {"k_factor": -5, "home_advantage": 0},
        {"k_factor": math.nan, "home_advantage": 0},
        {"k_factor": 20, "home_advantage": -10},
        {"k_factor": 20, "home_advantage": math.inf},
        {"k_factor": 20, "home_advantage": 0, "initial_rating": math.nan},
    ],
)
def test_invalid_parameters_are_rejected(parameters):
    with pytest.raises(ValueError):
        EloRatings(**parameters)


@pytest.mark.parametrize(
    ("home_team", "away_team", "home_goals", "away_goals"),
    [("A", "A", 1, 0), ("", "B", 1, 0), ("A", "B", -1, 0)],
)
def test_invalid_game_results_are_rejected(home_team, away_team, home_goals, away_goals):
    with pytest.raises(ValueError):
        GameResult(FIRST_DAY, home_team, away_team, home_goals, away_goals)


def test_ratings_property_is_a_copy():
    elo = new_league()

    elo.ratings["A"] = 9999

    assert elo.rating("A") == 1500


# --- draw model: from expected score to home/draw/away probabilities ---

HAND_EXPECTED = [0.3, 0.4, 0.6, 0.7, 0.8]
HAND_ACTUAL = [0.5, 0.0, 1.0, 0.5, 0.5]  # draws at 0.3, 0.7 and 0.8; 3 of 5 overall


def test_draw_rates_per_bin_without_a_prior():
    model = DrawModel.fit(HAND_EXPECTED, HAND_ACTUAL, bins=2, prior_weight=0)

    assert model.draw_rates == pytest.approx((1 / 2, 2 / 3))
    assert model.overall_draw_rate == pytest.approx(3 / 5)
    assert model.matches == 5


def test_prior_pulls_small_bins_towards_the_overall_draw_rate():
    model = DrawModel.fit(HAND_EXPECTED, HAND_ACTUAL, bins=2, prior_weight=5)

    # bin 0: (1 + 5 * 0.6) / (2 + 5) = 4/7;  bin 1: (2 + 5 * 0.6) / (3 + 5) = 5/8
    assert model.draw_rates == pytest.approx((4 / 7, 5 / 8))


def test_an_empty_bin_uses_the_overall_draw_rate():
    model = DrawModel.fit(HAND_EXPECTED, HAND_ACTUAL, bins=4, prior_weight=0)

    assert model.draw_rates == pytest.approx((3 / 5, 1 / 2, 1 / 2, 1.0))


def test_outcome_probabilities_without_the_cap():
    model = DrawModel(draw_rates=(0.25,), overall_draw_rate=0.25, matches=100)

    assert model.outcome_probabilities(0.6) == pytest.approx((0.475, 0.25, 0.275))


def test_draw_probability_is_capped_so_that_each_win_keeps_one_percent():
    model = DrawModel(draw_rates=(0.6,), overall_draw_rate=0.6, matches=100)

    # E = 0.1: the cap is 2 * 0.1 - 0.02 = 0.18, so P(H) = 0.1 - 0.09 = 0.01.
    assert model.outcome_probabilities(0.1) == pytest.approx((0.01, 0.18, 0.81))
    # E = 0.95: the cap is 2 * 0.05 - 0.02 = 0.08, so P(A) = 0.05 - 0.04 = 0.01.
    assert model.outcome_probabilities(0.95) == pytest.approx((0.91, 0.08, 0.01))


@pytest.mark.parametrize("expected", [0.01, 0.05, 0.3, 0.5, 0.93, 0.951, 0.99])
def test_each_win_keeps_at_least_one_percent(expected):
    model = DrawModel(draw_rates=(0.9,), overall_draw_rate=0.9, matches=100)

    home, draw, away = model.outcome_probabilities(expected)

    assert min(home, away) >= 0.01 - 1e-12
    assert draw >= 0


@pytest.mark.parametrize("expected", [0.05, 0.3, 0.5, 0.93, 0.951])
def test_no_result_is_called_impossible_inside_the_limits(expected):
    model = DrawModel(draw_rates=(0.9,), overall_draw_rate=0.9, matches=100)

    assert min(model.outcome_probabilities(expected)) > 0


@pytest.mark.parametrize("expected", [0.0, 0.01, 0.2, 0.5, 0.64, 0.93, 0.999, 1.0])
def test_outcome_probabilities_are_valid_and_keep_the_expected_score(expected):
    model = DrawModel.fit(HAND_EXPECTED, HAND_ACTUAL, bins=2, prior_weight=5)

    home, draw, away = model.outcome_probabilities(expected)

    assert min(home, draw, away) >= 0
    assert home + draw + away == pytest.approx(1, abs=1e-9)
    assert home + draw / 2 == pytest.approx(expected, abs=1e-12)


def test_fit_recovers_draw_rates_that_depend_on_the_expected_score():
    generator = random.Random(42)
    expected_scores, actual_scores = [], []
    for _ in range(20_000):
        expected = generator.random()
        true_draw_rate = 0.30 if 0.4 <= expected < 0.6 else 0.15
        if generator.random() < true_draw_rate:
            actual = 0.5
        else:
            actual = 1.0 if generator.random() < expected else 0.0
        expected_scores.append(expected)
        actual_scores.append(actual)

    model = DrawModel.fit(expected_scores, actual_scores, bins=10)

    assert model.draw_rates[4:6] == pytest.approx((0.30, 0.30), abs=0.04)
    for rate in (*model.draw_rates[:4], *model.draw_rates[6:]):
        assert rate == pytest.approx(0.15, abs=0.03)


def test_fitting_is_deterministic():
    first = DrawModel.fit(HAND_EXPECTED, HAND_ACTUAL)
    second = DrawModel.fit(HAND_EXPECTED, HAND_ACTUAL)

    assert first == second


def test_probabilities_for_a_match_from_the_current_ratings():
    elo = new_league(home_advantage=100)
    model = DrawModel(draw_rates=(0.25,), overall_draw_rate=0.25, matches=1)

    probabilities = model.outcome_probabilities(elo.expected_home_score("A", "B"))

    assert probabilities == pytest.approx((0.515065, 0.25, 0.234935), abs=1e-6)


@pytest.mark.parametrize(
    ("expected_scores", "actual_scores", "options"),
    [
        ([], [], {}),
        ([0.5, 0.6], [1.0], {}),
        ([1.2], [1.0], {}),
        ([0.5], [0.7], {}),
        ([0.5], [1.0], {"bins": 0}),
        ([0.5], [1.0], {"prior_weight": -1}),
    ],
)
def test_invalid_fitting_data_is_rejected(expected_scores, actual_scores, options):
    with pytest.raises(ValueError):
        DrawModel.fit(expected_scores, actual_scores, **options)


@pytest.mark.parametrize("expected", [-0.1, 1.5, math.nan])
def test_expected_scores_outside_zero_to_one_are_rejected(expected):
    model = DrawModel(draw_rates=(0.25,), overall_draw_rate=0.25, matches=1)

    with pytest.raises(ValueError):
        model.outcome_probabilities(expected)


@pytest.mark.parametrize("draw_rates", [(), (1.2,), (-0.1, 0.3)])
def test_draw_rates_must_be_probabilities(draw_rates):
    with pytest.raises(ValueError):
        DrawModel(draw_rates=draw_rates, overall_draw_rate=0.25, matches=1)
