"""End-to-end tests: raw season files -> database -> backtest log -> evaluation -> the screens.

Each test runs the whole chain on the small synthetic seasons of conftest.py and checks that the
layers agree with each other, or that a broken input is reported in the window instead of
stopping the application.
"""

import pytest

from app.evaluation.backtesting import read_log
from app.evaluation.evaluator import evaluate
from app.services.catalog import DataCatalog
from app.ui import main_window
from app.ui.main_window import MainWindow
from app.ui.widgets import OUTCOME_NAMES, number, percent

MODELS = ("Elo", "Poisson", "Logistic regression")


def table_rows(table):
    return [
        [table.item(row, column).text() for column in range(table.columnCount())]
        for row in range(table.rowCount())
    ]


@pytest.fixture
def window(app_context):
    window = MainWindow(app_context)
    yield window
    window.close()


@pytest.fixture
def window_with_log(window):
    window.dashboard.backtest_button.click()
    return window


def test_every_played_match_shows_the_forecasts_of_the_backtest_log(
    window_with_log, app_context, errors
):
    log = read_log(app_context.evaluation.log)
    logged = {(row.match_date, row.home_team, row.away_team, row.model): row for row in log}
    tab = window_with_log.match_prediction
    tab.season_box.setCurrentText("2007-08")

    for index in range(tab.match_box.count()):
        tab.match_box.setCurrentIndex(index)
        match = tab.match_box.currentData()
        tab.predict_button.click()

        rows = {
            model: logged[(match.match_date, match.home_team, match.away_team, model)]
            for model in MODELS
        }
        assert table_rows(tab.probability_table) == [
            [
                model,
                percent(rows[model].p_home),
                percent(rows[model].p_draw),
                percent(rows[model].p_away),
                OUTCOME_NAMES[rows[model].predicted],
            ]
            for model in MODELS
        ]
        poisson = rows["Poisson"]
        assert tab.goals_label.text() == (
            f"Expected goals: {match.home_team} {number(poisson.expected_home_goals, 2)}, "
            f"{match.away_team} {number(poisson.expected_away_goals, 2)}"
        )
    assert tab.match_box.count() == 12
    assert errors == []


def test_the_screens_show_the_evaluation_of_the_log(window_with_log, app_context, errors):
    evaluations = evaluate(read_log(app_context.evaluation.log))
    window_with_log.tabs.setCurrentWidget(window_with_log.algorithm_comparison)

    assert table_rows(window_with_log.dashboard.results_table) == [
        [
            e.model,
            percent(e.accuracy.value),
            number(e.brier.value if e.brier else None),
            number(e.log_loss.value if e.log_loss else None),
        ]
        for e in evaluations
    ]
    assert table_rows(window_with_log.algorithm_comparison.metrics_table) == [
        [
            e.model,
            percent(e.accuracy.value),
            number(e.brier.value if e.brier else None),
            number(e.log_loss.value if e.log_loss else None),
            number(e.calibration_error),
            number(e.goals_error.value if e.goals_error else None, 3),
        ]
        for e in evaluations
    ]
    assert errors == []


@pytest.mark.parametrize("season", ["2006-07", "2007-08"])
def test_the_league_table_matches_the_raw_files(window, raw_season_rows, next_season_rows, season):
    raw_rows = raw_season_rows if season == "2006-07" else next_season_rows
    records = {}
    for row in raw_rows:
        home_goals, away_goals = int(row["FTHG"]), int(row["FTAG"])
        for team, scored, conceded in (
            (row["HomeTeam"], home_goals, away_goals),
            (row["AwayTeam"], away_goals, home_goals),
        ):
            played, wins, draws, losses, goals_for, goals_against = records.get(team, [0] * 6)
            records[team] = [
                played + 1,
                wins + (scored > conceded),
                draws + (scored == conceded),
                losses + (scored < conceded),
                goals_for + scored,
                goals_against + conceded,
            ]
    expected = sorted(
        records.items(),
        key=lambda item: (
            -(3 * item[1][1] + item[1][2]),
            -(item[1][4] - item[1][5]),
            -item[1][4],
            item[0],
        ),
    )
    tab = window.team_analysis
    tab.season_box.setCurrentText(season)

    tab.show_button.click()

    assert table_rows(tab.standings_table) == [
        [
            str(position),
            team,
            *(str(value) for value in record),
            str(record[4] - record[5]),
            str(3 * record[1] + record[2]),
        ]
        for position, (team, record) in enumerate(expected, start=1)
    ]


def test_a_missing_database_is_explained_at_start_up(application, monkeypatch, tmp_path):
    shown = []

    class MessageBox:
        @staticmethod
        def critical(parent, title, text):
            shown.append(text)

    monkeypatch.setattr(main_window, "QMessageBox", MessageBox)
    monkeypatch.setattr(
        main_window, "default_context", lambda: DataCatalog.load(tmp_path / "missing.db")
    )

    assert main_window.main() == 1
    assert len(shown) == 1
    assert "python -m app.data.build_database" in shown[0]


def test_a_damaged_log_is_explained_in_place_and_can_be_rebuilt(app_context, errors):
    log = app_context.evaluation.log
    log.parent.mkdir(parents=True)
    log.write_text("not,a,prediction,log\n1,2,3,4\n", encoding="utf-8")

    window = MainWindow(app_context)
    dashboard, comparison = window.dashboard, window.algorithm_comparison

    for label in (dashboard.results_label, comparison.summary_label):
        assert "is not a prediction log" in label.text()
        assert "Run the backtest again" in label.text()
    assert not dashboard.backtest_button.isHidden()
    assert not comparison.backtest_button.isHidden()
    window.tabs.setCurrentWidget(comparison)  # changing tabs repeats no dialog
    assert errors == []

    dashboard.backtest_button.click()
    window.tabs.setCurrentWidget(window.dashboard)

    assert dashboard.results_table.rowCount() == 5
    assert dashboard.backtest_button.isHidden()
    assert comparison.backtest_button.isHidden()
    assert comparison.metrics_table.rowCount() == 5
    assert errors == []
    window.close()


def test_a_backtest_that_fails_is_reported_and_the_window_keeps_working(
    app_context, database, errors
):
    window = MainWindow(app_context)
    database.unlink()  # the data is already loaded; the backtest reads the database again

    window.dashboard.backtest_button.click()

    assert len(errors) == 1
    assert "Database not found" in errors[0]
    assert window.dashboard.backtest_button.isEnabled()
    assert not window.dashboard.backtest_button.isHidden()
    window.team_analysis.show_button.click()  # the loaded data still works
    assert window.team_analysis.standings_table.rowCount() == 4
    assert len(errors) == 1
    window.close()
