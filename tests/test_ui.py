"""Headless tests of the screens: built off-screen, driven by their own buttons, read back."""

import os
import time
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QCoreApplication, QDate, QThread  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.services.catalog import DataCatalog  # noqa: E402
from app.services.evaluation import EvaluationService  # noqa: E402
from app.services.predictions import PredictionService  # noqa: E402
from app.services.teams import TeamService  # noqa: E402
from app.ui.context import AppContext  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402
from app.ui.worker import run_in_background, run_now  # noqa: E402


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def errors():
    return []


@pytest.fixture
def window(application, database, tmp_path, errors):
    catalog = DataCatalog.load(database)
    context = AppContext(
        catalog=catalog,
        predictions=PredictionService(catalog.matches, min_training_matches=3),
        teams=TeamService(catalog.matches),
        evaluation=EvaluationService(
            tmp_path / "results" / "log.csv",
            database,
            first_evaluation_season="2007-08",
            min_training_matches=3,
        ),
        run_task=run_now,
        report_error=errors.append,
    )
    main_window = MainWindow(context)
    yield main_window
    main_window.close()


def cells(table, column):
    return [table.item(row, column).text() for row in range(table.rowCount())]


def test_the_window_has_four_tabs_and_prepares_predictions(window):
    titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]

    assert titles == ["Dashboard", "Match Prediction", "Team Analysis", "Algorithm Comparison"]
    assert window.statusBar().currentMessage() == "Predictions ready"


def test_dashboard_summary_and_backtest(window):
    dashboard = window.dashboard

    assert (
        "La Liga, 2 seasons (2006-07 to 2007-08), 24 matches, 4 teams"
        in dashboard.data_label.text()
    )
    assert dashboard.results_table.isHidden()
    dashboard.backtest_button.click()

    assert not dashboard.results_table.isHidden()
    assert cells(dashboard.results_table, 0) == [
        "Elo",
        "Poisson",
        "Logistic regression",
        "Past frequencies",
        "Always home win",
    ]


def test_predicting_a_played_match(window):
    tab = window.match_prediction
    assert tab.season_box.currentText() == "2007-08"  # latest season first
    tab.match_box.setCurrentIndex(3)

    tab.predict_button.click()

    assert cells(tab.probability_table, 0) == ["Elo", "Poisson", "Logistic regression"]
    assert tab.result_label.text().startswith("Actual result:")
    assert tab.scores_table.rowCount() == 5
    assert tab.goals_label.text().startswith("Expected goals:")
    assert tab.predict_button.isEnabled()


def test_predicting_a_hypothetical_fixture(window):
    tab = window.match_prediction
    tab.fixture_button.setChecked(True)
    tab.home_box.setCurrentText("Alpha")
    tab.away_box.setCurrentText("Bravo")
    tab.date_edit.setDate(QDate(2007, 9, 5))

    tab.predict_button.click()

    assert tab.result_label.text() == "Not played: a hypothetical fixture."
    assert tab.probability_table.rowCount() == 3


def test_an_impossible_fixture_is_reported_not_crashed(window, errors):
    tab = window.match_prediction
    tab.fixture_button.setChecked(True)
    tab.home_box.setCurrentText("Alpha")
    tab.away_box.setCurrentText("Alpha")

    tab.predict_button.click()

    assert any("itself" in message for message in errors)
    assert tab.predict_button.isEnabled()


def test_team_analysis_for_a_whole_season(window):
    tab = window.team_analysis
    tab.season_box.setCurrentText("2006-07")
    tab.team_box.setCurrentText("Alpha")

    tab.show_button.click()

    assert cells(tab.standings_table, 1) == ["Alpha", "Bravo", "Charlie", "Delta"]
    assert cells(tab.standings_table, 9) == ["11", "9", "7", "5"]
    assert tab.overview_labels["Position"].text() == "1 of 4"
    assert tab.overview_labels["Last 5 results"].text() == "W W D W D"
    assert tab.overview_labels["Season group"].text() != "Season not finished at this date"


def test_team_analysis_as_of_a_date(window):
    tab = window.team_analysis
    tab.season_box.setCurrentText("2006-07")
    tab.team_box.setCurrentText("Charlie")
    tab.whole_season_box.setChecked(False)
    tab.date_edit.setDate(QDate(2006, 9, 4))

    tab.show_button.click()

    assert cells(tab.standings_table, 1) == ["Alpha", "Bravo", "Delta", "Charlie"]
    assert tab.overview_labels["Position"].text() == "4 of 4"
    assert tab.overview_labels["Season group"].text() == "Season not finished at this date"


def test_algorithm_comparison_after_the_backtest(window):
    tab = window.algorithm_comparison
    assert not tab.backtest_button.isHidden()

    tab.backtest_button.click()

    assert tab.backtest_button.isHidden()
    assert tab.metrics_table.rowCount() == 5
    assert tab.differences_table.rowCount() > 0
    assert tab.agreement_table.rowCount() == 3
    assert cells(tab.breakdown_table, 0) == ["2007-08"]
    tab.breakdown_box.setCurrentText("By actual result")
    assert set(cells(tab.breakdown_table, 0)) <= {"Home win", "Draw", "Away win"}


def wait_for(condition, seconds=10.0):
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def test_background_tasks_report_back_on_the_ui_thread(application):
    results, threads, failures = [], [], []

    def finished(value):
        results.append(value)
        threads.append(QThread.currentThread())

    run_in_background(lambda: sum(range(10)), finished, failures.append)
    run_in_background(lambda: 1 / 0, results.append, failures.append)
    wait_for(lambda: results and failures)

    assert results == [45]
    assert threads == [application.thread()]
    assert failures == ["division by zero"]


def test_run_now_uses_the_same_contract():
    results, failures = [], []

    run_now(lambda: date(2007, 9, 5), results.append, failures.append)
    run_now(lambda: int("x"), results.append, failures.append)

    assert results == [date(2007, 9, 5)]
    assert len(failures) == 1


def test_numbers_are_right_aligned_and_labels_are_not(application):
    from PySide6.QtCore import Qt

    from app.ui.widgets import fill_table, make_table

    table = make_table(["Season", "Brier", "Change", "Share", "Score"])
    fill_table(table, [["2010-11", "0.5506", "-0.0073", "53.4%", "2-1"]])

    right = [
        bool(table.item(0, column).textAlignment() & Qt.AlignmentFlag.AlignRight)
        for column in range(5)
    ]
    assert right == [False, True, True, True, False]
