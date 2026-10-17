from datetime import date

import numpy as np
import pytest

from app.evaluation.backtesting import (
    ALWAYS_HOME_WIN,
    MODEL_ORDER,
    PredictionLogRow,
    run_backtest,
    write_log,
)
from app.evaluation.evaluator import evaluate, main
from app.evaluation.metrics import (
    CONFIDENCE_THRESHOLDS,
    brier_score,
    calibration_table,
    confident_accuracy,
    expected_calibration_error,
)

# The four hand-worked forecasts of tests/test_metrics.py: results H, A, H, D.
FORECASTS = [(0.5, 0.3, 0.2), (0.2, 0.5, 0.3), (0.6, 0.2, 0.2), (1 / 3, 1 / 3, 1 / 3)]
SCORES = [(1, 0), (0, 2), (2, 1), (1, 1)]
ACTUAL = ["H", "A", "H", "D"]


def row(index: int, model: str, probabilities, expected_goals=None) -> PredictionLogRow:
    home_goals, away_goals = SCORES[index]
    p_home, p_draw, p_away = probabilities
    return PredictionLogRow(
        match_date=date(2010, 9, index + 1),
        season="2010-11",
        home_team="Alpha",
        away_team="Bravo",
        home_goals=home_goals,
        away_goals=away_goals,
        actual=ACTUAL[index],
        model=model,
        p_home=p_home,
        p_draw=p_draw,
        p_away=p_away,
        predicted="HDA"[list(probabilities).index(max(probabilities))],
        expected_home_goals=None if expected_goals is None else expected_goals[0],
        expected_away_goals=None if expected_goals is None else expected_goals[1],
        home_group="0",
        away_group="1",
    )


@pytest.fixture
def log():
    rows = []
    for i, forecast in enumerate(FORECASTS):
        rows.append(row(i, "Poisson", forecast, expected_goals=(1.5, 1.0)))
        rows.append(row(i, ALWAYS_HOME_WIN, (1.0, 0.0, 0.0)))
    return rows


def test_models_are_scored_with_the_metrics(log):
    poisson, home_win = evaluate(log)
    probabilities = np.array(FORECASTS)
    actual = np.array([0, 2, 0, 1])

    assert (poisson.model, poisson.matches) == ("Poisson", 4)
    assert poisson.accuracy.value == 0.5
    assert poisson.brier.value == pytest.approx(brier_score(probabilities, actual).value)
    assert poisson.log_loss.value == pytest.approx(0.876640, abs=1e-6)
    table = calibration_table(probabilities, actual)
    assert poisson.calibration_error == pytest.approx(expected_calibration_error(table))
    np.testing.assert_array_equal(poisson.confusion, [[2, 0, 0], [1, 0, 0], [0, 1, 0]])
    assert [c.threshold for c in poisson.confident] == list(CONFIDENCE_THRESHOLDS)
    assert poisson.confident[0] == confident_accuracy(probabilities, actual, 0.5)
    assert home_win.model == ALWAYS_HOME_WIN
    assert home_win.confident == ()  # always 100% sure: nothing to tell


def test_expected_goals_error_pools_home_and_away_goals(log):
    poisson = evaluate(log)[0]

    # Expected 1.5-1.0 against 1-0, 0-2, 2-1 and 1-1: errors 0.5 + 1, 1.5 + 1, 0.5 + 0, 0.5 + 0.
    assert poisson.goals_error.value == pytest.approx(5 / 8)
    assert poisson.goals_error.count == 8


def test_always_home_win_is_scored_on_accuracy_only(log):
    home_win = evaluate(log)[1]

    assert home_win.accuracy.value == 0.5
    np.testing.assert_array_equal(home_win.confusion, [[2, 0, 0], [1, 0, 0], [1, 0, 0]])
    assert home_win.brier is None
    assert home_win.log_loss is None
    assert home_win.calibration is None
    assert home_win.goals_error is None


def test_models_must_cover_the_same_matches(log):
    with pytest.raises(ValueError, match="different matches"):
        evaluate(log[:-1])
    with pytest.raises(ValueError, match="empty"):
        evaluate([])


def test_models_follow_the_log_order(season_matches, next_season_matches):
    backtest = run_backtest(
        [*season_matches, *next_season_matches],
        first_evaluation_season="2007-08",
        min_training_matches=3,
    )

    evaluations = evaluate(backtest.rows)

    assert [evaluation.model for evaluation in evaluations] == list(MODEL_ORDER)
    assert all(evaluation.matches == 12 for evaluation in evaluations)
    poisson = next(e for e in evaluations if e.model == "Poisson")
    assert poisson.goals_error is not None
    assert all(e.goals_error is None for e in evaluations if e.model != "Poisson")


def test_main_prints_every_model(season_matches, next_season_matches, tmp_path, capsys):
    backtest = run_backtest(
        [*season_matches, *next_season_matches],
        first_evaluation_season="2007-08",
        min_training_matches=3,
    )
    path = tmp_path / "log.csv"
    write_log(backtest.rows, path)

    exit_code = main(path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Evaluation of 12 matches" in output
    for model in MODEL_ORDER:
        assert model in output


def test_main_explains_a_missing_log(tmp_path, capsys):
    assert main(tmp_path / "missing.csv") == 1
    assert "python -m app.evaluation.backtesting" in capsys.readouterr().err


def test_a_single_match_prints_without_a_standard_error(log, tmp_path, capsys):
    single = log[:2]  # Poisson and Always home win for the first match
    path = tmp_path / "single.csv"
    write_log(single, path)

    assert main(path) == 0
    assert "Evaluation of 1 matches" in capsys.readouterr().out
