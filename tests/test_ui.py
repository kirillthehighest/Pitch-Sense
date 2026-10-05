"""Headless tests of the screens: built off-screen, driven by their own buttons, read back."""

import time
from datetime import date

import pytest
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QCoreApplication, QDate, Qt, QThread
from PySide6.QtGui import QColor

from app.services.preferences import FavouriteTeam, Preferences
from app.ui.brand import flag_pixmap
from app.ui.main_window import MainWindow
from app.ui.match_prediction import SAME_TEAM
from app.ui.team_analysis import GROUPS_NEED_WHOLE_SEASON, SEASON_NOT_FINISHED
from app.ui.widgets import (
    BarRow,
    ChartView,
    FormStrip,
    HeroBanner,
    LeagueButton,
    ProbabilityBars,
    StatTile,
    fill_table,
    make_table,
)
from app.ui.worker import run_in_background, run_now
from app.visualization.palette import GOLD_TINT

PAGE_TITLES = ["ACASĂ", "PREDICȚIE", "ECHIPE", "MODELE", "LIGI"]
MODEL_NAMES = [
    "Elo",
    "Poisson",
    "Regresie logistică",
    "Frecvențele trecute",
    "Mereu victoria gazdelor",
]


@pytest.fixture
def window(app_context):
    main_window = MainWindow(app_context)
    yield main_window
    main_window.close()


def cells(table, column):
    return [table.item(row, column).text() for row in range(table.rowCount())]


def highlighted(table):
    return [
        row
        for row in range(table.rowCount())
        if table.item(row, 0).background().color() == QColor(GOLD_TINT)
    ]


def chart_title(chart_view):
    return chart_view.figure.axes[0].get_title("left")


def chart_legend(chart_view):
    return [text.get_text() for text in chart_view.figure.axes[0].get_legend().get_texts()]


# --- the window ---


def test_charts_wait_for_results(window):
    charts = (
        window.match_prediction.score_chart,
        window.team_analysis.elo_chart,
        window.team_analysis.groups_chart,
        window.algorithm_comparison.calibration_chart,
        window.algorithm_comparison.confusion_chart,
        window.leagues.skill_chart,
        window.leagues.home_chart,
    )

    assert all(chart.figure is None for chart in charts)
    assert all(chart.message_label.text() for chart in charts)


def test_the_sidebar_leads_to_five_screens_and_the_header_names_them(window):
    assert [button.text() for button in window.nav_buttons] == PAGE_TITLES
    assert window.stack.currentIndex() == 0
    assert window.page_title.text() == "ACASĂ"

    window.nav_buttons[3].click()

    assert window.stack.currentIndex() == 3
    assert window.nav_buttons[3].isChecked() and not window.nav_buttons[0].isChecked()
    assert window.page_title.text() == "MODELE"
    assert window.page_subtitle.text() == window.algorithm_comparison.subtitle


def test_the_window_prepares_the_predictions_of_the_league(window, app_context):
    assert window.current_league == "SP1"
    assert window.league_buttons["SP1"].isChecked()
    assert window.hero.eyebrow_label.text() == "LA LIGA · SPANIA · 2006/07–2007/08"
    assert not window.hero.flag_label.pixmap().isNull()
    assert app_context.league("SP1").predictions.is_prepared
    assert window.statusBar().currentMessage() == "Predicțiile pentru La Liga sunt gata"
    assert window.windowTitle().startswith("PitchSense")
    assert not window.windowIcon().isNull()


# --- Acasă ---


def test_home_summarizes_the_league_and_offers_the_backtest(window):
    home = window.home
    values = {name: tile.value_label.text() for name, tile in home.stat_tiles.items()}

    assert values == {"Meciuri": "24", "Sezoane": "2", "Echipe": "4", "Meciuri evaluate": "–"}
    assert home.stat_tiles["Meciuri"].name_label.text() == "MECIURI"
    assert home.results_table.isHidden()
    assert home.best_label.text() == "–"
    home.backtest_button.click()

    assert home.stat_tiles["Meciuri evaluate"].value_label.text() == "12"
    assert not home.results_table.isHidden()
    assert home.backtest_button.isHidden()
    assert cells(home.results_table, 0) == MODEL_NAMES
    assert home.best_label.text() in MODEL_NAMES[:3]
    assert home.results_label.text().startswith("12 meciuri din sezoanele 2007/08–2007/08")


# --- Echipa ta ---


def choose_favourite(window, league_name, team):
    dialog = window.open_favourite_dialog()
    dialog.league_box.setCurrentText(league_name)
    dialog.team_box.setCurrentText(team)
    dialog.save_button.click()
    return dialog


def test_your_team_is_saved_shown_and_highlighted(window, app_context, tmp_path):
    assert window.favourite_button.text() == "Alege echipa ta"
    assert window.home.favourite_label.text() == "–"

    choose_favourite(window, "La Liga", "Charlie")

    assert app_context.preferences.favourite == FavouriteTeam("SP1", "Charlie")
    assert Preferences(tmp_path / "preferences.json").favourite == FavouriteTeam("SP1", "Charlie")
    assert window.favourite_button.text() == "Echipa ta: Charlie"
    home = window.home
    assert home.favourite_label.text() == "Charlie"
    assert home.favourite_caption.text() == "La Liga, 2007/08: locul 3 din 4, 7 puncte."
    assert len(home.favourite_form.results) == 5
    assert not home.favourite_badge.pixmap().isNull()
    assert home.favourite_button.text() == "Schimbă echipa"
    prediction = window.match_prediction
    last = prediction.match_box.currentData()
    assert "Charlie" in (last.home_team, last.away_team)
    later = [prediction.match_box.itemData(i) for i in range(prediction.match_box.count())]
    assert all("Charlie" not in (m.home_team, m.away_team) for m in later[later.index(last) + 1 :])
    assert prediction.home_box.currentText() == "Charlie"
    team = window.team_analysis
    assert team.team_box.currentText() == "Charlie"
    team.show_button.click()
    assert cells(team.standings_table, 1)[highlighted(team.standings_table)[0]] == "Charlie"


def test_the_dialog_starts_from_your_team_and_can_forget_it(window, app_context):
    choose_favourite(window, "La Liga", "Bravo")

    dialog = window.open_favourite_dialog()
    assert (dialog.league_box.currentText(), dialog.team_box.currentText()) == ("La Liga", "Bravo")
    assert [dialog.team_box.itemText(i) for i in range(dialog.team_box.count())] == [
        "Alpha",
        "Bravo",
        "Charlie",
        "Delta",
    ]
    dialog.clear_button.click()

    assert app_context.preferences.favourite is None
    assert window.favourite_button.text() == "Alege echipa ta"
    assert window.home.favourite_label.text() == "–"
    assert window.home.favourite_form.results == ()


def test_cancelling_the_dialog_changes_nothing(window, app_context):
    dialog = window.open_favourite_dialog()
    dialog.team_box.setCurrentText("Delta")
    dialog.cancel_button.click()

    assert app_context.preferences.favourite is None
    assert window.favourite_button.text() == "Alege echipa ta"


# --- more than one league ---


@pytest.fixture
def two_league_context(make_app_context, two_league_database):
    return make_app_context(two_league_database, ("E0", "SP1"))


def test_choosing_a_league_shows_it_on_every_screen_and_is_remembered(two_league_context):
    window = MainWindow(two_league_context)
    assert window.current_league == "E0"  # nothing remembered: the first league
    assert window.hero.eyebrow_label.text().startswith("PREMIER LEAGUE · ANGLIA")
    assert [button.text() for button in window.league_buttons.values()] == [
        "Premier League",
        "La Liga",
    ]

    window.league_buttons["SP1"].click()

    assert window.current_league == "SP1"
    assert window.league_buttons["SP1"].isChecked() and not window.league_buttons["E0"].isChecked()
    assert window.hero.eyebrow_label.text().startswith("LA LIGA · SPANIA")
    assert window.match_prediction.home_box.itemText(0) == "Alpha"
    assert window.team_analysis.team_box.itemText(0) == "Alpha"
    assert window.statusBar().currentMessage() == "Predicțiile pentru La Liga sunt gata"
    assert two_league_context.league("SP1").predictions.is_prepared
    assert two_league_context.preferences.competition == "SP1"
    window.close()

    again = MainWindow(two_league_context)
    assert again.current_league == "SP1"
    again.close()


def test_your_team_from_another_league_brings_its_league(two_league_context):
    window = MainWindow(two_league_context)

    choose_favourite(window, "La Liga", "Delta")

    assert window.current_league == "SP1"
    assert window.team_analysis.team_box.currentText() == "Delta"
    window.close()


def test_the_leagues_screen_compares_every_league_after_their_backtests(two_league_context):
    window = MainWindow(two_league_context)
    leagues = window.leagues
    assert "Premier League, La Liga" in leagues.summary_label.text()
    assert not leagues.backtest_button.isHidden()

    leagues.backtest_button.click()

    assert leagues.backtest_button.isHidden()
    assert cells(leagues.models_table, 0) == ["Premier League", "La Liga"]
    assert cells(leagues.character_table, 0) == ["Premier League", "La Liga"]
    assert cells(leagues.differences_table, 0) == ["Premier League", "La Liga", "Toate ligile"]
    assert highlighted(leagues.models_table) == [0]  # the league on screen
    assert leagues.summary_label.text().startswith("2 ligi, 24 de meciuri de evaluare.")
    assert [bars.get_label() for bars in leagues.skill_chart.figure.axes[0].containers] == [
        "Elo",
        "Poisson",
        "Regresie logistică",
    ]
    assert leagues.home_chart.figure is None  # the fixture seasons have no 2020/21
    card = leagues.cards["SP1"]
    assert card.value_label.text().endswith("%")
    assert card.goals_label.text().endswith("goluri pe meci")
    assert card.best_label.text() in MODEL_NAMES[:3]
    assert leagues.cards["E0"].property("role") == "favourite"  # the league on screen
    card.clicked.emit("SP1")  # a click on a card opens its league
    assert window.current_league == "SP1"
    assert highlighted(leagues.models_table) == [1]
    assert leagues.cards["SP1"].property("role") == "favourite"
    assert leagues.cards["E0"].property("role") == "card"
    window.close()


# --- Predicție ---


def test_predicting_a_played_match(window):
    tab = window.match_prediction
    assert tab.season_box.currentText() == "2007/08"  # latest season first
    tab.match_box.setCurrentIndex(3)

    tab.predict_button.click()

    assert cells(tab.probability_table, 0) == ["Elo", "Poisson", "Regresie logistică"]
    assert [row.label for row in tab.bars.rows] == ["Elo", "Poisson", "Regresie logistică"]
    assert all(row.home + row.draw + row.away == pytest.approx(1) for row in tab.bars.rows)
    match = tab.match_box.currentData()
    assert tab.score_label.text() == f"{match.home_goals} – {match.away_goals}"
    assert (tab.home_name.text(), tab.away_name.text()) == (
        match.home_team.upper(),
        match.away_team.upper(),
    )
    assert not tab.home_badge.pixmap().isNull()
    assert tab.result_label.text().startswith("Rezultat real:")
    assert tab.scores_table.rowCount() == 5
    assert tab.goals_label.text().startswith("Goluri așteptate:")
    assert tab.predict_button.isEnabled()
    assert chart_title(tab.score_chart).startswith("Probabilitatea fiecărui scor (Poisson")
    assert tab.score_chart.message_label.isHidden()


def test_predicting_a_hypothetical_fixture(window):
    tab = window.match_prediction
    tab.fixture_button.setChecked(True)
    tab.home_box.setCurrentText("Alpha")
    tab.away_box.setCurrentText("Bravo")
    tab.date_edit.setDate(QDate(2007, 9, 5))

    tab.predict_button.click()

    assert tab.result_label.text() == "Meci nejucat: o predicție ipotetică."
    assert tab.probability_table.rowCount() == 3
    assert tab.fixture_label.text() == "LA LIGA · 2007/08 · 05.09.2007"
    assert tab.score_label.text() == "VS"


def test_a_team_cannot_play_itself(window, errors):
    tab = window.match_prediction
    tab.fixture_button.setChecked(True)
    tab.home_box.setCurrentText("Alpha")
    tab.away_box.setCurrentText("Alpha")

    tab.predict_button.click()

    assert tab.status_label.text() == SAME_TEAM
    assert tab.probability_table.rowCount() == 0
    assert tab.predict_button.isEnabled()
    assert errors == []


def test_a_failed_prediction_is_reported_not_crashed(window, app_context, errors, monkeypatch):
    def fail(*_):
        raise ValueError("no such fixture")

    monkeypatch.setattr(app_context.league("SP1").predictions, "predict", fail)
    tab = window.match_prediction

    tab.predict_button.click()

    assert errors == ["no such fixture"]
    assert tab.predict_button.isEnabled()
    assert tab.status_label.text() == ""


# --- Echipe ---


def test_team_analysis_for_a_whole_season(window):
    tab = window.team_analysis
    tab.season_box.setCurrentText("2006/07")
    tab.team_box.setCurrentText("Alpha")

    tab.show_button.click()

    assert cells(tab.standings_table, 1) == ["Alpha", "Bravo", "Charlie", "Delta"]
    assert cells(tab.standings_table, 9) == ["11", "9", "7", "5"]
    assert highlighted(tab.standings_table) == [0]  # the team shown
    assert not tab.standings_table.item(0, 1).icon().isNull()  # the team's badge
    assert tab.team_label.text() == "ALPHA"
    assert tab.overview_labels["Poziție"].text() == "locul 1 din 4"
    assert tab.form_strip.letters == "V V E V E"
    assert tab.overview_labels["Grupul sezonului"].text() != SEASON_NOT_FINISHED
    assert [tab.views.tabText(i) for i in range(tab.views.count())] == [
        "CLASAMENT",
        "RATING ELO",
        "GRUPURI",
    ]
    assert chart_title(tab.elo_chart) == "Alpha: ratingul Elo înaintea fiecărui meci"
    assert chart_legend(tab.elo_chart) == ["2006/07"]
    assert chart_title(tab.groups_chart).startswith("Grupurile echipelor, 2006/07")


def test_team_analysis_as_of_a_date(window):
    tab = window.team_analysis
    tab.season_box.setCurrentText("2006/07")
    tab.team_box.setCurrentText("Charlie")
    tab.whole_season_box.setChecked(False)
    tab.date_edit.setDate(QDate(2006, 9, 4))

    tab.show_button.click()

    assert cells(tab.standings_table, 1) == ["Alpha", "Bravo", "Delta", "Charlie"]
    assert tab.overview_labels["Poziție"].text() == "locul 4 din 4, înainte de 04.09.2006"
    assert tab.overview_labels["Grupul sezonului"].text() == SEASON_NOT_FINISHED
    assert chart_legend(tab.elo_chart) == ["2006/07", "Meciuri până la 04.09.2006"]
    assert tab.groups_chart.figure is None
    assert tab.groups_chart.message_label.text() == GROUPS_NEED_WHOLE_SEASON


# --- Modele ---


def test_algorithm_comparison_after_the_backtest(window):
    tab = window.algorithm_comparison
    assert not tab.backtest_button.isHidden()

    tab.backtest_button.click()

    assert tab.backtest_button.isHidden()
    assert cells(tab.metrics_table, 0) == MODEL_NAMES
    assert tab.differences_table.rowCount() > 0
    assert tab.agreement_table.rowCount() == 3
    assert cells(tab.breakdown_table, 0) == ["2007/08"]
    tab.breakdown_box.setCurrentText("Pe rezultatul real")
    assert set(cells(tab.breakdown_table, 0)) <= {"Victorie gazde", "Egal", "Victorie oaspeți"}
    assert chart_legend(tab.calibration_chart)[:2] == ["Calibrare perfectă", "Elo"]
    models = [tab.confusion_box.itemText(i) for i in range(tab.confusion_box.count())]
    assert models == MODEL_NAMES
    assert chart_title(tab.confusion_chart) == "Elo: matricea de confuzie"
    tab.confusion_box.setCurrentText("Regresie logistică")
    assert chart_title(tab.confusion_chart) == "Regresie logistică: matricea de confuzie"
    tab.refresh()  # showing the results again keeps the chosen model
    assert chart_title(tab.confusion_chart) == "Regresie logistică: matricea de confuzie"


# --- building blocks ---


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
    view = ChartView("Nimic încă")
    first, second = Figure(), Figure()

    view.show_figure(first)
    view.show_figure(second)

    assert view.figure is second
    assert len(view.findChildren(FigureCanvasQTAgg)) == 1
    assert view.message_label.isHidden()
    view.show_message("Indisponibil")
    assert view.figure is None
    assert view.findChildren(FigureCanvasQTAgg) == []
    assert not view.message_label.isHidden()
    assert view.message_label.text() == "Indisponibil"


def test_numbers_are_right_aligned_and_labels_are_not(application):
    table = make_table(["Sezon", "Brier", "Diferență", "Parte", "Scor", "Meciuri"])
    fill_table(table, [["2010/11", "0,5506", "−0,0073", "53,4%", "2–1", "6.080"]])

    right = [
        bool(table.item(0, column).textAlignment() & Qt.AlignmentFlag.AlignRight)
        for column in range(6)
    ]
    assert right == [False, True, True, True, False, True]


def test_highlighted_rows_are_tinted_and_bold(application):
    table = make_table(["Echipă", "Pct."])
    fill_table(table, [["Alpha", "11"], ["Bravo", "9"]], highlight={1})

    assert highlighted(table) == [1]
    assert table.item(1, 1).font().bold() and not table.item(0, 1).font().bold()


def test_probability_bars_keep_one_row_per_model_and_grow_with_them(application):
    bars = ProbabilityBars()
    assert bars.height() == 0

    bars.set_rows([BarRow("Elo", 0.5, 0.3, 0.2), BarRow("Poisson", 0.4, 0.3, 0.3)])
    bars.resize(600, bars.height())

    assert [row.label for row in bars.rows] == ["Elo", "Poisson"]
    assert bars.height() == 2 * ProbabilityBars.ROW_HEIGHT + ProbabilityBars.LEGEND_HEIGHT
    assert not bars.grab().isNull()


def test_the_form_strip_shows_romanian_letters_and_refuses_unknown_results(application):
    strip = FormStrip()

    strip.set_results(["W", "D", "L"])

    assert strip.letters == "V E Î"
    assert strip.width() == 3 * FormStrip.SQUARE + 2 * FormStrip.GAP
    with pytest.raises(ValueError, match="unknown result codes"):
        strip.set_results(["W", "X"])


def test_a_league_button_is_checkable_and_names_its_country(application):
    button = LeagueButton("SP1", "La Liga", "Spania", flag_pixmap("SP1", 24))

    button.click()

    assert button.isChecked()
    assert (button.code, button.text(), button.country) == ("SP1", "La Liga", "Spania")
    assert not button.grab().isNull()


def test_the_hero_writes_titles_and_eyebrows_in_capitals(application):
    hero = HeroBanner()

    hero.show_page("Echipe", "Clasamentul la orice dată.")
    hero.show_league("La Liga · Spania", None)

    assert hero.title_label.text() == "ECHIPE"
    assert hero.subtitle_label.text() == "Clasamentul la orice dată."
    assert hero.eyebrow_label.text() == "LA LIGA · SPANIA"
    assert not hero.grab().isNull()


def test_a_stat_tile_shows_a_value_under_a_capital_name(application):
    tile = StatTile("Meciuri")

    tile.set_value("7.600")

    assert (tile.value_label.text(), tile.name_label.text()) == ("7.600", "MECIURI")
