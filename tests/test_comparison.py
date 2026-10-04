import math
from datetime import date

import numpy as np
import pytest

from app.evaluation.backtesting import (
    ALWAYS_HOME_WIN,
    PredictionLogRow,
    run_backtest,
    write_log,
)
from app.evaluation.comparison import (
    Measure,
    agreements,
    all_agree,
    by_group_pair,
    by_matchup_type,
    by_outcome,
    by_season,
    largest_disagreements,
    main,
    matchup_type,
    paired_difference,
    paired_differences,
    per_match_scores,
    total_variation_distance,
)
from app.evaluation.metrics import brier_per_match, correct_per_match, log_loss_per_match

# Three matches (results H, H, A) forecast by two models; A is better on every match.
FIRST = [(0.6, 0.2, 0.2), (0.5, 0.3, 0.2), (0.2, 0.3, 0.5)]  # Brier 0.24, 0.38, 0.38
SECOND = [(0.5, 0.3, 0.2), (0.4, 0.3, 0.3), (0.3, 0.3, 0.4)]  # Brier 0.38, 0.54, 0.54
RESULTS = [("H", 1, 0), ("H", 2, 0), ("A", 0, 1)]


def row(index: int, model: str, probabilities) -> PredictionLogRow:
    actual, home_goals, away_goals = RESULTS[index]
    return PredictionLogRow(
        match_date=date(2010, 9, index + 1),
        season="2010-11",
        home_team="Alpha",
        away_team="Bravo",
        home_goals=home_goals,
        away_goals=away_goals,
        actual=actual,
        model=model,
        p_home=probabilities[0],
        p_draw=probabilities[1],
        p_away=probabilities[2],
        predicted="HDA"[list(probabilities).index(max(probabilities))],
        expected_home_goals=None,
        expected_away_goals=None,
        home_group="0",
        away_group="1",
    )


@pytest.fixture
def log():
    rows = []
    for i in range(3):
        rows.append(row(i, "Elo", FIRST[i]))
        rows.append(row(i, "Poisson", SECOND[i]))
        rows.append(row(i, ALWAYS_HOME_WIN, (1.0, 0.0, 0.0)))
    return rows


def test_per_match_values_match_the_hand_example():
    probabilities = np.array([[0.5, 0.3, 0.2], [0.2, 0.5, 0.3], [0.6, 0.2, 0.2], [1 / 3] * 3])
    actual = np.array([0, 2, 0, 1])

    np.testing.assert_allclose(brier_per_match(probabilities, actual), [0.38, 0.78, 0.24, 2 / 3])
    np.testing.assert_allclose(
        log_loss_per_match(probabilities, actual),
        [-math.log(0.5), -math.log(0.3), -math.log(0.6), math.log(3)],
    )
    np.testing.assert_array_equal(correct_per_match(probabilities, actual), [1, 0, 1, 0])


def test_paired_difference_hand_example():
    # d = 0.24 - 0.38, 0.38 - 0.54, 0.38 - 0.54 = -0.14, -0.16, -0.16
    result = paired_difference(
        np.array([0.24, 0.38, 0.38]), np.array([0.38, 0.54, 0.54]), "A", "B", Measure.BRIER
    )

    standard_error = np.std([-0.14, -0.16, -0.16], ddof=1) / math.sqrt(3)
    assert result.mean == pytest.approx(-0.46 / 3)
    assert result.standard_error == pytest.approx(standard_error)
    assert standard_error == pytest.approx(0.0066667, abs=1e-6)
    assert (result.lower, result.upper) == pytest.approx(
        (-0.46 / 3 - 1.96 * standard_error, -0.46 / 3 + 1.96 * standard_error)
    )
    assert result.significant
    assert result.better == "A"


def test_identical_models_cannot_be_told_apart():
    values = np.array([0.3, 0.5, 0.7])

    result = paired_difference(values, values, "A", "B", Measure.BRIER)

    assert (result.mean, result.standard_error) == (0.0, 0.0)
    assert not result.significant
    assert result.better is None


def test_for_accuracy_the_higher_value_wins():
    result = paired_difference(
        np.array([1.0, 1.0, 1.0, 0.0]), np.array([0.0, 0.0, 0.0, 0.0]), "A", "B", Measure.ACCURACY
    )

    assert result.mean == 0.75
    assert result.better == ("A" if result.significant else None)


def test_swapping_the_models_flips_the_difference():
    forward = paired_difference(
        np.array([0.2, 0.4, 0.1]), np.array([0.3, 0.3, 0.5]), "A", "B", Measure.LOG_LOSS
    )
    backward = paired_difference(
        np.array([0.3, 0.3, 0.5]), np.array([0.2, 0.4, 0.1]), "B", "A", Measure.LOG_LOSS
    )

    assert backward.mean == pytest.approx(-forward.mean)
    assert backward.standard_error == pytest.approx(forward.standard_error)
    assert backward.better == forward.better


def test_paired_differences_from_a_log(log):
    results = paired_differences(log, pairs=[("Elo", "Poisson")])

    by_measure = {result.measure: result for result in results}
    assert set(by_measure) == set(Measure)
    assert by_measure[Measure.BRIER].mean == pytest.approx(-0.46 / 3)
    assert by_measure[Measure.BRIER].better == "Elo"


def test_always_home_win_is_compared_on_accuracy_only(log):
    scores = per_match_scores(log)

    assert set(scores[ALWAYS_HOME_WIN]) == {Measure.ACCURACY}
    results = paired_differences(log, pairs=[("Elo", ALWAYS_HOME_WIN)])
    assert [result.measure for result in results] == [Measure.ACCURACY]


def test_models_must_cover_the_same_matches(log):
    with pytest.raises(ValueError, match="different matches"):
        per_match_scores(log[:-1])
    with pytest.raises(ValueError, match="not in the log"):
        paired_differences(log, pairs=[("Elo", "Logistic regression")])
    with pytest.raises(ValueError):
        paired_difference(np.array([0.1]), np.array([0.2]), "A", "B", Measure.BRIER)


def test_main_prints_the_paired_differences(season_matches, next_season_matches, tmp_path, capsys):
    backtest = run_backtest(
        [*season_matches, *next_season_matches],
        first_evaluation_season="2007-08",
        min_training_matches=3,
    )
    path = tmp_path / "log.csv"
    write_log(backtest.rows, path)

    assert main(path) == 0
    output = capsys.readouterr().out
    assert "Paired differences on 12 matches" in output
    assert "Elo" in output and "Past frequencies" in output


def test_main_explains_a_missing_log(tmp_path, capsys):
    assert main(tmp_path / "missing.csv") == 1
    assert "python -m app.evaluation.backtesting" in capsys.readouterr().err


# --- breakdowns ---

FORECASTS_BY_MODEL = {
    "Elo": [(0.6, 0.2, 0.2), (0.5, 0.3, 0.2), (0.2, 0.3, 0.5), (0.3, 0.4, 0.3)],
    "Poisson": [(0.5, 0.3, 0.2), (0.4, 0.3, 0.3), (0.3, 0.3, 0.4), (0.4, 0.3, 0.3)],
    "Logistic regression": [
        (0.55, 0.25, 0.2),
        (0.45, 0.3, 0.25),
        (0.25, 0.3, 0.45),
        (0.35, 0.35, 0.3),
    ],
    "Past frequencies": [(0.45, 0.25, 0.3)] * 4,
}
MATCHES = [  # season, result, home goals, away goals, home group, away group
    ("2010-11", "H", 1, 0, "0", "3"),
    ("2010-11", "H", 2, 0, "2", "2"),
    ("2011-12", "A", 0, 1, "promoted", "1"),
    ("2011-12", "D", 1, 1, "1", "3"),
]


@pytest.fixture
def four_model_log():
    rows = []
    for index, (season, actual, home_goals, away_goals, home_group, away_group) in enumerate(
        MATCHES
    ):
        for model, forecasts in FORECASTS_BY_MODEL.items():
            p_home, p_draw, p_away = forecasts[index]
            rows.append(
                PredictionLogRow(
                    match_date=date(2010 + index // 2, 9, index + 1),
                    season=season,
                    home_team=f"Home{index}",
                    away_team=f"Away{index}",
                    home_goals=home_goals,
                    away_goals=away_goals,
                    actual=actual,
                    model=model,
                    p_home=p_home,
                    p_draw=p_draw,
                    p_away=p_away,
                    predicted="HDA"[[p_home, p_draw, p_away].index(max(p_home, p_draw, p_away))],
                    expected_home_goals=None,
                    expected_away_goals=None,
                    home_group=home_group,
                    away_group=away_group,
                )
            )
    return rows


def brier_of(model: str, indices: list[int]) -> float:
    probabilities = np.array([FORECASTS_BY_MODEL[model][i] for i in indices])
    actual = np.array(["HDA".index(MATCHES[i][1]) for i in indices])
    return float(brier_per_match(probabilities, actual).mean())


@pytest.mark.parametrize(
    ("home_group", "away_group", "expected"),
    [
        ("promoted", "0", "promoted team involved"),
        ("3", "promoted", "promoted team involved"),
        ("0", "2", "elite team involved"),
        ("0", "0", "elite team involved"),
        ("2", "2", "same group"),
        ("1", "3", "different groups"),
    ],
)
def test_matchup_types(home_group, away_group, expected):
    assert matchup_type(home_group, away_group) == expected


def test_breakdown_by_season(four_model_log):
    seasons = by_season(four_model_log)

    assert [(s.label, s.matches) for s in seasons] == [("2010-11", 2), ("2011-12", 2)]
    first = seasons[0]
    for model in FORECASTS_BY_MODEL:
        assert first.brier[model].value == pytest.approx(brier_of(model, [0, 1]))
    # 2010-11: Elo 0.31, logistic regression 0.38, Poisson 0.46.
    assert (first.best, first.runner_up) == ("Elo", "Logistic regression")
    assert first.lead.mean == pytest.approx(
        brier_of("Elo", [0, 1]) - brier_of("Logistic regression", [0, 1])
    )


def test_breakdown_by_outcome_follows_home_draw_away(four_model_log):
    outcomes = by_outcome(four_model_log)

    assert [(o.label, o.matches) for o in outcomes] == [("H", 2), ("D", 1), ("A", 1)]
    assert outcomes[1].lead is None  # a single match cannot be tested
    assert outcomes[1].brier["Poisson"].value == pytest.approx(brier_of("Poisson", [3]))


def test_breakdown_by_matchup_type(four_model_log):
    types = by_matchup_type(four_model_log)

    assert [t.label for t in types] == [
        "promoted team involved",
        "elite team involved",
        "same group",
        "different groups",
    ]
    assert all(t.matches == 1 for t in types)


def test_group_pairs_need_enough_matches(four_model_log):
    assert by_group_pair(four_model_log, min_matches=2) == []
    assert [p.label for p in by_group_pair(four_model_log, min_matches=1)] == [
        "0 v 3",
        "1 v 3",
        "2 v 2",
        "promoted v 1",
    ]


def test_breakdowns_need_every_compared_model(four_model_log):
    without_logistic = [row for row in four_model_log if row.model != "Logistic regression"]

    with pytest.raises(ValueError, match="not in the log"):
        by_season(without_logistic)


# --- agreement ---


def test_total_variation_distance_hand_values():
    first = np.array([[0.6, 0.2, 0.2], [0.3, 0.3, 0.4], [1.0, 0.0, 0.0]])
    second = np.array([[0.5, 0.3, 0.2], [0.3, 0.3, 0.4], [0.0, 0.0, 1.0]])

    np.testing.assert_allclose(total_variation_distance(first, second), [0.1, 0.0, 1.0])


def test_agreement_between_two_models(log):
    (agreement,) = agreements(log, models=("Elo", "Poisson"))

    # Both predict H, H, A; every forecast differs by 0.1 on two outcomes.
    assert (agreement.first, agreement.second, agreement.matches) == ("Elo", "Poisson", 3)
    assert agreement.same_prediction == 1.0
    assert agreement.mean_distance == pytest.approx(0.1)


def test_all_three_models_agree_on_three_of_four_matches(four_model_log):
    # In the last match Elo predicts a draw while the other two predict a home win.
    assert all_agree(four_model_log) == 0.75
    assert len(agreements(four_model_log)) == 3


def test_largest_disagreements_come_first():
    rows = []
    for index, (elo, poisson) in enumerate(
        [((0.6, 0.2, 0.2), (0.5, 0.3, 0.2)), ((0.2, 0.3, 0.5), (0.7, 0.2, 0.1))]
    ):
        rows.append(row(index, "Elo", elo))
        rows.append(row(index, "Poisson", poisson))

    (largest,) = largest_disagreements(rows, count=1, models=("Elo", "Poisson"))

    assert largest.row.match_date == date(2010, 9, 2)
    assert largest.largest_distance == pytest.approx(0.5)  # (0.5 + 0.1 + 0.4) / 2
    assert largest.forecasts == {"Elo": (0.2, 0.3, 0.5), "Poisson": (0.7, 0.2, 0.1)}


def test_agreement_needs_the_models(log):
    with pytest.raises(ValueError, match="not in the log"):
        agreements(log, models=("Elo", "Logistic regression"))
