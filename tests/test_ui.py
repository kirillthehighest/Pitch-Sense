"""Headless tests of the screens: built off-screen, driven by their own buttons, read back."""

import time
from datetime import date

import pytest
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QCoreApplication, QDate, QThread

from app.ui.main_window import MainWindow
from app.ui.team_analysis import GROUPS_NEED_WHOLE_SEASON
from app.ui.widgets import ChartView
from app.ui.worker import run_in_background, run_now


@pytest.fixture
def window(app_context):
    main_window = MainWindow(app_context)
    yield main_window
    main_window.close()


def cells(table, column):
    return [table.item(row, column).text() for row in range(table.rowCount())]


def chart_title(chart_view):
    return chart_view.figure.axes[0].get_title()


def chart_legend(chart_view):
    return [text.get_text() for text in chart_view.figure.axes[0].get_legend().get_texts()]


def test_charts_wait_for_results(window):
    charts = (
        window.match_prediction.score_chart,
        window.team_analysis.elo_chart,
        window.team_analysis.groups_chart,
        window.algorithm_comparison.calibration_chart,
        window.algorithm_comparison.confusion_chart,
    )

    assert all(chart.figure is None for chart in charts)
    assert all(chart.message_label.text() for chart in charts)


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
    assert chart_title(tab.score_chart).startswith("Poisson: probability of each score")
    assert tab.score_chart.message_label.isHidden()


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
    assert [tab.views.tabText(i) for i in range(tab.views.count())] == [
        "League table",
        "Elo rating",
        "Team groups",
    ]
    assert chart_title(tab.elo_chart) == "Alpha: Elo rating before each match"
    assert chart_legend(tab.elo_chart) == ["2006-07"]
    assert chart_title(tab.groups_chart).startswith("Team groups in 2006-07")


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
    assert chart_legend(tab.elo_chart) == ["2006-07", "Matches before 2006-09-04"]
    assert tab.groups_chart.figure is None
    assert tab.groups_chart.message_label.text() == GROUPS_NEED_WHOLE_SEASON


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
    assert chart_legend(tab.calibration_chart)[:2] == ["Perfect calibration", "Elo"]
    models = [tab.confusion_box.itemText(i) for i in range(tab.confusion_box.count())]
    assert models == cells(tab.metrics_table, 0)
    assert chart_title(tab.confusion_chart) == "Elo: confusion matrix"
    tab.confusion_box.setCurrentText("Poisson")
    assert chart_title(tab.confusion_chart) == "Poisson: confusion matrix"
    tab.refresh()  # showing the results again keeps the chosen model
    assert chart_title(tab.confusion_chart) == "Poisson: confusion matrix"


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


def test_a_chart_view_shows_one_figure_or_a_message(application):
    view = ChartView("Nothing yet")
    first, second = Figure(), Figure()

    view.show_figure(first)
    view.show_figure(second)

    assert view.figure is second
    assert len(view.findChildren(FigureCanvasQTAgg)) == 1
    assert view.message_label.isHidden()
    view.show_message("Not available")
    assert view.figure is None
    assert view.findChildren(FigureCanvasQTAgg) == []
    assert not view.message_label.isHidden()
    assert view.message_label.text() == "Not available"


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
