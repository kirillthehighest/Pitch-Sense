"""Headless tests of the screens: built off-screen, driven by their own buttons, read back."""

import time
from datetime import date

import pytest
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QCoreApplication, Qt, QThread
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QWidget

from app import __version__
from app.data.live import update_live_data
from app.data.models import Outcome
from app.prediction.outputs import ModelName
from app.services.preferences import FavouriteTeam, Preferences
from app.services.teams import FIRST_SEASON_NAME, GROUP_NAMES
from app.ui.analysis import TABS
from app.ui.brand import flag_pixmap
from app.ui.main_window import (
    COMPACT_LOGO_WIDTH,
    COMPACT_SIDE_PANEL_WIDTH,
    COMPACT_WIDTH,
    SIDE_PANEL_WIDTH,
    UPDATE,
    MainWindow,
)
from app.ui.match_detail import MODEL_EXPLANATIONS
from app.ui.match_widgets import DayStrip, MatchRow, chip_text
from app.ui.matches import NO_MATCHES, next_match_day
from app.ui.team_page import GROUPS_IN_PROGRESS, SEASON_NOT_FINISHED
from app.ui.theme import style_sheet
from app.ui.themes import THEMES, current_theme
from app.ui.widgets import (
    BarRow,
    ChartView,
    FormStrip,
    HeroBanner,
    LeagueButton,
    ProbabilityBars,
    ReflowGrid,
    ResponsiveBox,
    StatTile,
    fill_table,
    make_table,
)
from app.ui.worker import run_in_background, run_now
from app.visualization.palette import LOSS, WIN
from tests.conftest import LIVE_TODAY

PAGE_TITLES = ["MECIURI", "CLASAMENT", "ECHIPE", "ANALIZĂ"]
MODEL_NAMES = [
    "Elo",
    "Poisson",
    "Regresie logistică",
    "Frecvențele trecute",
    "Mereu victoria gazdelor",
]
OUTCOME_MODELS = ["Elo", "Poisson", "Regresie logistică"]


@pytest.fixture
def window(app_context):
    app_context.today = lambda: date(2007, 9, 4)  # in the middle of 2007-08
    main_window = MainWindow(app_context)
    yield main_window
    main_window.close()


def cells(table, column):
    return [table.item(row, column).text() for row in range(table.rowCount())]


def highlighted(table):
    return [
        row
        for row in range(table.rowCount())
        if table.item(row, 0).background().color() == QColor(current_theme().accent_tint)
    ]


def chart_title(chart_view):
    return chart_view.figure.axes[0].get_title("left")


def chart_legend(chart_view):
    return [text.get_text() for text in chart_view.figure.axes[0].get_legend().get_texts()]


def day_rows(page):
    return [row for group in page.groups for row in group.rows]


# --- the window ---


def test_charts_wait_for_results(window):
    charts = (
        window.matches.detail.score_chart,
        window.analysis.models.calibration_chart,
        window.analysis.models.confusion_chart,
        window.analysis.leagues.skill_chart,
        window.analysis.leagues.home_chart,
    )

    assert all(chart.figure is None for chart in charts)
    assert all(chart.message_label.text() for chart in charts)


def test_the_top_bar_leads_to_four_screens_and_the_header_names_them(window):
    assert [button.text() for button in window.nav_buttons] == PAGE_TITLES
    assert window.stack.currentIndex() == 0
    assert window.page_title.text() == "MECIURI"

    window.nav_buttons[3].click()

    assert window.stack.currentIndex() == 3
    assert window.nav_buttons[3].isChecked() and not window.nav_buttons[0].isChecked()
    assert window.page_title.text() == "ANALIZĂ"
    assert window.page_subtitle.text() == window.analysis.subtitle


def test_the_window_prepares_the_predictions_of_the_league(window, app_context):
    assert window.current_league == "SP1"
    assert window.league_buttons["SP1"].isChecked()
    assert window.hero.eyebrow_label.text() == "LA LIGA · SPANIA · 2006/07–2007/08"
    assert not window.hero.flag_label.pixmap().isNull()
    assert window.hero.photo is not None  # the La Liga image
    assert window.hero.credit_label.text() == "Imagine: DAZN"
    assert 0 <= window.hero.top < 0.5
    assert app_context.league("SP1").predictions.is_prepared
    assert window.statusBar().currentMessage() == "Predicțiile pentru La Liga sunt gata"
    assert window.windowTitle().startswith("PitchSense")
    assert not window.windowIcon().isNull()
    assert window.version_note.text().startswith(f"PitchSense {__version__}\n")


# --- Meciuri ---


def test_the_matches_open_on_the_next_day_with_matches(window):
    page = window.matches

    assert page.day == date(2007, 9, 4)  # "today" has a match
    assert page.day_label.text() == "AZI · MAR. 4 SEPT."
    assert [chip.isChecked() for chip in page.day_strip.chips] == [False] * 3 + [True] + [False] * 3
    assert page.day_strip.chips[3].text() == "AZI\n4 SEPT."
    (row,) = day_rows(page)
    assert (row.forecast.home_team, row.forecast.away_team) == ("Bravo", "Alpha")
    assert row.model is ModelName.LOGISTIC_REGRESSION  # the default model
    assert page.groups[0].code == "SP1"
    assert next_match_day([date(2007, 9, 1), date(2007, 9, 6)], date(2007, 9, 4)) == date(
        2007, 9, 6
    )
    assert next_match_day([date(2007, 9, 1)], date(2007, 9, 4)) == date(2007, 9, 1)


def test_a_played_match_shows_its_score_and_whether_the_model_was_right(window):
    page = window.matches
    page.show_day(date(2007, 9, 3))

    (row,) = day_rows(page)

    played = row.forecast.played
    assert row.status_text == "Final"
    prediction = row.forecast.of(ModelName.LOGISTIC_REGRESSION)
    assert row.hit == (prediction.probabilities.most_likely == played.result)
    assert not row.grab().isNull()


def test_a_played_match_says_right_or_wrong_with_a_shape_and_a_colour(window):
    window.matches.show_day(date(2007, 9, 3))
    forecast = day_rows(window.matches)[0].forecast
    for model in ModelName:
        row = MatchRow(forecast, model)
        row.resize(700, MatchRow.HEIGHT)
        image = row.grab().toImage()
        best = (Outcome.HOME_WIN, Outcome.DRAW, Outcome.AWAY_WIN).index(
            forecast.of(model).probabilities.most_likely
        )
        width = MatchRow.PROBABILITY_WIDTH
        chip_left = 700 - 12 - 3 * width - 2 * 6 + best * (width + 6)
        mark = image.pixelColor(round(chip_left + width - 1), round(MatchRow.HEIGHT / 2 - 15 - 4))

        assert mark.name() == (WIN if row.hit else LOSS).lower()


def test_the_chosen_model_fills_the_list(window):
    page = window.matches

    page.model_box.setCurrentText("Elo")

    assert all(row.model is ModelName.ELO for row in day_rows(page))


def test_the_day_strip_moves_a_week_at_a_time(window):
    page = window.matches

    page.day_strip.later_button.click()

    assert page.day == date(2007, 9, 11)
    assert page.day_strip.chips[3].isChecked()
    page.day_strip.chips[0].click()
    assert page.day == date(2007, 9, 8)
    page.show_day(date(2007, 10, 20))
    assert day_rows(page) == []
    assert not page.empty_label.isHidden()
    assert page.empty_label.text() == NO_MATCHES
    assert page.day_strip.chips[3].property("empty") is True


def test_a_match_page_shows_every_model_its_scores_and_both_teams(window):
    page = window.matches
    page.show_day(date(2007, 9, 3))
    (row,) = day_rows(page)

    row.click()

    detail = page.detail
    played = row.forecast.played
    assert page.views.currentIndex() == 1
    assert [bar.label for bar in detail.bars.rows] == OUTCOME_MODELS
    assert all(bar.home + bar.draw + bar.away == pytest.approx(1) for bar in detail.bars.rows)
    assert detail.hero.score.text() == f"{played.home_goals} – {played.away_goals}"
    assert detail.hero.status.text() == "FINAL"
    assert detail.hero.eyebrow.text() == "LA LIGA · 2007/08 · 03.09.2007"
    assert detail.verdict.text().startswith(f"Rezultat: {played.home_goals}–{played.away_goals}")
    assert detail.knowledge.text() == (
        "Predicțiile au fost făcute din meciurile jucate înainte de 03.09.2007, fără să știe "
        "rezultatul."
    )
    assert len(detail.explanations) == len(MODEL_EXPLANATIONS) == 3
    assert detail.scores_table.rowCount() == 5
    assert detail.goals_label.text().startswith("Goluri așteptate:")
    assert chart_title(detail.score_chart).startswith("Probabilitatea fiecărui scor (Poisson")
    assert detail.home_column.place.text().startswith("Locul ")
    assert len(detail.home_column.form.results) <= 5
    assert detail.home_column.rating.text().startswith("Rating Elo: ")

    detail.back_button.click()
    assert page.views.currentIndex() == 0


def test_a_team_name_on_a_match_page_opens_the_team(window):
    page = window.matches
    page.show_day(date(2007, 9, 3))
    day_rows(page)[0].click()

    page.detail.away_column.name_button.click()

    assert window.stack.currentIndex() == window.pages.index(window.team_page)
    assert window.team_page.team_box.currentText() == page.detail.forecast.away_team


def test_predicting_a_hypothetical_fixture(window):
    dialog = window.matches.open_hypothetical()
    dialog.season_box.setCurrentText("2007/08")
    dialog.home_box.setCurrentText("Alpha")
    dialog.away_box.setCurrentText("Bravo")
    dialog.date_edit.setDate(date(2007, 9, 5))

    dialog.predict_button.click()

    detail = window.matches.detail
    assert window.matches.views.currentIndex() == 1
    assert detail.knowledge.text() == (
        "Meci ipotetic: predicțiile folosesc meciurile jucate înainte de 05.09.2007."
    )
    assert detail.hero.status.text() == "MECI IPOTETIC"
    assert detail.hero.score.text() == "VS"
    assert len(detail.bars.rows) == 3


def test_a_team_cannot_play_itself(window, errors):
    dialog = window.matches.open_hypothetical()
    dialog.home_box.setCurrentText("Alpha")
    dialog.away_box.setCurrentText("Alpha")

    dialog.predict_button.click()

    assert dialog.status.text() == "Alege două echipe diferite."
    assert window.matches.views.currentIndex() == 0
    assert dialog.predict_button.isEnabled()
    assert errors == []


def test_a_failed_prediction_is_reported_not_crashed(window, app_context, errors, monkeypatch):
    def fail(*_):
        raise ValueError("no such fixture")

    monkeypatch.setattr(app_context.league("SP1").predictions, "predict", fail)
    dialog = window.matches.open_hypothetical()

    dialog.predict_button.click()

    assert errors == ["no such fixture"]
    assert dialog.predict_button.isEnabled()
    assert dialog.status.text() == ""


# --- Echipa ta ---


def choose_favourite(window, league_name, team):
    dialog = window.open_favourite_dialog()
    dialog.league_box.setCurrentText(league_name)
    dialog.team_box.setCurrentText(team)
    dialog.save_button.click()
    return dialog


def test_your_team_is_saved_shown_and_highlighted(window, app_context, tmp_path):
    assert window.favourite_button.text() == "Alege echipa ta"
    assert not window.matches.favourite_choose_button.isHidden()

    choose_favourite(window, "La Liga", "Charlie")

    assert app_context.preferences.favourite == FavouriteTeam("SP1", "Charlie")
    assert Preferences(tmp_path / "preferences.json").favourite == FavouriteTeam("SP1", "Charlie")
    assert window.favourite_button.text() == "Echipa ta: Charlie"
    page = window.matches
    assert page.favourite_name.text() == "CHARLIE"
    assert page.favourite_caption.text() == "La Liga · 2007/08"
    assert len(page.favourite_form.results) == 5
    assert len(page.favourite_rows) == 1  # the last result; the season is over
    assert page.favourite_rows[0].stacked
    assert page.favourite_choose_button.isHidden()
    assert not page.favourite_badge.pixmap().isNull()
    assert window.team_page.team_box.currentText() == "Charlie"
    standings = window.standings
    assert cells(standings.table, 1)[highlighted(standings.table)[0]] == "Charlie"
    page.favourite_open_button.click()
    assert window.stack.currentIndex() == window.pages.index(window.team_page)


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
    assert window.matches.favourite_form.results == ()
    assert not window.matches.favourite_choose_button.isHidden()


def test_cancelling_the_dialog_changes_nothing(window, app_context):
    dialog = window.open_favourite_dialog()
    dialog.team_box.setCurrentText("Delta")
    dialog.cancel_button.click()

    assert app_context.preferences.favourite is None
    assert window.favourite_button.text() == "Alege echipa ta"


# --- more than one league ---


@pytest.fixture
def two_league_context(make_app_context, two_league_database):
    context = make_app_context(two_league_database, ("E0", "SP1"))
    context.today = lambda: date(2007, 9, 4)
    return context


def test_choosing_a_league_shows_it_on_every_screen_and_is_remembered(two_league_context):
    window = MainWindow(two_league_context)
    assert window.current_league == "E0"  # nothing remembered: the first league
    assert window.hero.eyebrow_label.text().startswith("PREMIER LEAGUE · ANGLIA")
    assert [button.text() for button in window.league_buttons.values()] == [
        "Premier League",
        "La Liga",
    ]
    assert all(two_league_context.league(c).predictions.is_prepared for c in ("E0", "SP1"))

    window.league_buttons["SP1"].click()

    assert window.current_league == "SP1"
    assert window.league_buttons["SP1"].isChecked() and not window.league_buttons["E0"].isChecked()
    assert window.hero.eyebrow_label.text().startswith("LA LIGA · SPANIA")
    assert window.team_page.team_box.itemText(0) == "Alpha"
    assert cells(window.standings.table, 1)[0] in ("Alpha", "Bravo", "Charlie", "Delta")
    assert two_league_context.preferences.competition == "SP1"
    window.close()

    again = MainWindow(two_league_context)
    assert again.current_league == "SP1"
    again.close()


def test_the_matches_of_every_league_come_with_the_chosen_league_first(two_league_context):
    window = MainWindow(two_league_context)
    page = window.matches

    assert [group.code for group in page.groups] == ["E0", "SP1"]
    window.league_buttons["SP1"].click()
    assert [group.code for group in page.groups] == ["SP1", "E0"]
    page.league_button.click()  # only the chosen league
    assert [group.code for group in page.groups] == ["SP1"]
    assert page.league_button.text() == "Doar La Liga"
    page.all_button.click()
    assert len(page.groups) == 2

    page.groups[1].standings_button.click()  # the other league's table

    assert window.current_league == "E0"
    assert window.stack.currentIndex() == window.pages.index(window.standings)
    window.close()


def test_your_team_from_another_league_brings_its_league(two_league_context):
    window = MainWindow(two_league_context)

    choose_favourite(window, "La Liga", "Delta")

    assert window.current_league == "SP1"
    assert window.team_page.team_box.currentText() == "Delta"
    window.close()


def test_the_leagues_tab_compares_every_league_after_their_backtests(two_league_context):
    window = MainWindow(two_league_context)
    leagues = window.analysis.leagues
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


# --- Clasament ---


def test_the_table_shows_crests_and_form_and_opens_a_team(window):
    page = window.standings
    page.show_season("2006-07")

    assert cells(page.table, 1) == ["Alpha", "Bravo", "Charlie", "Delta"]
    assert cells(page.table, 9) == ["11", "9", "7", "5"]
    assert not page.table.item(0, 1).icon().isNull()  # the team's badge
    form = page.table.cellWidget(0, 10).findChild(FormStrip)
    assert form.letters == "V V E V E"
    assert page.title_label.text() == "LA LIGA 2006/07 · TOT SEZONUL"

    page.table.cellClicked.emit(2, 1)

    assert window.stack.currentIndex() == window.pages.index(window.team_page)
    assert window.team_page.team_box.currentText() == "Charlie"
    assert window.team_page.season_box.currentText() == "2006/07"


def test_the_table_as_of_a_date(window):
    page = window.standings
    page.show_season("2006-07")
    page.whole_season_box.setChecked(False)

    page.date_edit.setDate(date(2006, 9, 4))

    assert cells(page.table, 1) == ["Alpha", "Bravo", "Delta", "Charlie"]
    assert page.title_label.text() == "LA LIGA 2006/07 · ÎNAINTE DE 04.09.2006"


# --- Echipe ---


def test_the_page_of_a_team_for_a_whole_season(window):
    page = window.team_page

    page.show_team("Alpha", "2006-07")

    assert page.header.name.text() == "ALPHA"
    assert page.header.caption.text() == "2006/07 · locul 1 din 4 · sezon încheiat"
    values = {name: tile.value_label.text() for name, tile in page.tiles.items()}
    assert values["Loc"] == "1" and values["Puncte"] == "11" and values["Meciuri"] == "6"
    assert page.form_strip.letters == "V V E V E"
    assert page.pre_season_label.text() == FIRST_SEASON_NAME
    assert page.season_group_label.text() in GROUP_NAMES.values()
    assert len(page.match_rows) == 5  # the last five results; nothing left to play
    assert page.next_title.isHidden()
    assert chart_title(page.elo_chart) == "Alpha: ratingul Elo înaintea fiecărui meci"
    assert chart_legend(page.elo_chart) == ["2006/07"]
    assert chart_title(page.groups_chart).startswith("Grupurile echipelor, 2006/07")
    assert [page.views.tabText(i) for i in range(page.views.count())] == ["RATING ELO", "GRUPURI"]


def test_a_match_on_a_team_page_opens_its_page(window):
    page = window.team_page
    page.show_team("Alpha", "2006-07")

    page.match_rows[0].click()

    assert window.stack.currentIndex() == 0
    assert window.matches.views.currentIndex() == 1
    assert window.matches.detail.forecast is page.match_rows[0].forecast


# --- Analiză ---


def test_the_analysis_explains_scores_and_credits(window):
    analysis = window.analysis
    assert [analysis.views.tabText(i) for i in range(analysis.views.count())] == [
        tab.upper() for tab in TABS
    ]
    texts = " ".join(label.text() for label in analysis.findChildren(type(window.page_title)))
    assert "Ratingul Elo" in texts or "RATINGUL ELO" in texts
    assert "Wikipedia" in texts and "CC0" in texts
    assert "La Liga: imagine promoțională, sursa DAZN." in texts
    assert "nu se publică" in texts
    assert "209 steme în aplicație." in texts
    assert analysis.check_label.text().startswith("Sezonul în desfășurare nu a fost descărcat")


def test_algorithm_comparison_after_the_backtest(window):
    tab = window.analysis.models
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


# --- the season in progress (Phases 18 and 19) ---


@pytest.fixture
def live_window(make_app_context, database, live_dir):
    context = make_app_context(database, live_dir=live_dir)
    context.today = lambda: LIVE_TODAY  # 10 September 2008: matches until the 12th
    main_window = MainWindow(context)
    yield main_window
    main_window.close()


def test_the_matches_open_on_the_next_scheduled_day(live_window):
    page = live_window.matches

    assert page.day == date(2008, 9, 10)
    (row,) = day_rows(page)
    assert row.forecast.played is None
    assert row.status_text == "18:30"
    assert "Actualizat:" in live_window.version_note.text()

    row.click()

    detail = page.detail
    assert detail.hero.status.text() == "PROGRAMAT"
    assert detail.hero.eyebrow.text() == "LA LIGA · 2008/09 · 10.09.2008, 18:30"
    assert detail.knowledge.text() == (
        "Predicțiile folosesc toate meciurile jucate până acum (ultimele pe 07.09.2008)."
    )
    assert detail.verdict.isHidden()
    assert [bar.label for bar in detail.bars.rows] == OUTCOME_MODELS


def test_a_scheduled_day_already_past_is_marked_postponed(live_window):
    row = MatchRow(day_rows(live_window.matches)[0].forecast, ModelName.ELO)
    forecast = row.forecast
    late = type(forecast)(**{**forecast.__dict__, "match_date": date(2008, 9, 5)})

    assert MatchRow(late, ModelName.ELO).status_text == "Amânat"
    assert MatchRow(late, ModelName.ELO, show_date=True).status_text == "05.09"


def test_the_team_page_of_the_season_in_progress(live_window):
    page = live_window.team_page

    page.show_team("Alpha", "2008-09")

    assert page.header.caption.text().endswith("sezon în desfășurare")
    assert page.season_group_label.text() == SEASON_NOT_FINISHED
    assert page.groups_chart.message_label.text() == GROUPS_IN_PROGRESS
    assert not page.next_title.isHidden()
    assert page.match_rows[0].forecast.played is None  # the next match first
    assert page.match_rows[0].stacked


def test_the_analysis_scores_the_season_in_progress(live_window):
    analysis = live_window.analysis

    assert cells(analysis.check_table, 0) == OUTCOME_MODELS
    assert cells(analysis.check_table, 1) == ["7", "7", "7"]
    assert analysis.check_label.text().startswith(
        "La Liga 2008/09: 7 meciuri jucate între 01.09.2008 și 07.09.2008"
    )


def test_the_update_button_brings_the_season_in_progress(
    make_app_context, database, tmp_path, fake_fetch, four_team_league, errors
):
    target = tmp_path / "downloaded"

    def update():
        return update_live_data(
            target, ("SP1",), today=LIVE_TODAY, fetch=fake_fetch, competitions=four_team_league
        )

    context = make_app_context(database, live_dir=target, update_data=update)
    context.today = lambda: LIVE_TODAY
    window = MainWindow(context)
    assert window.standings.season_box.currentText() == "2007/08"
    assert "Sezonul curent: —" in window.version_note.text()

    window.update_button.click()

    assert errors == []
    assert window.standings.season_box.currentText() == "2008/09"
    assert window.matches.day == date(2008, 9, 10)
    assert day_rows(window.matches)[0].forecast.played is None
    assert window.statusBar().currentMessage() == (
        "Date actualizate. Sezonul 2008/09: 7 meciuri jucate și 5 meciuri programate în 1 ligă."
    )
    assert "Actualizat:" in window.version_note.text()
    assert window.update_button.isEnabled()
    assert window.update_button.text() == UPDATE
    window.close()


def test_a_failed_update_is_reported_and_keeps_the_data(window, errors):
    window.update_button.click()

    assert len(errors) == 1
    assert errors[0].startswith("Datele nu au putut fi actualizate; au rămas cele de până acum.")
    assert errors[0].endswith("tests never use the network>")
    assert window.standings.season_box.currentText() == "2007/08"
    assert window.update_button.isEnabled()


def test_a_damaged_season_in_progress_is_reported(make_app_context, database, live_dir, errors):
    (live_dir / "SP1.json").write_text("<html>", encoding="utf-8")

    window = MainWindow(make_app_context(database, live_dir=live_dir))

    assert len(errors) == 1
    assert errors[0].startswith("Sezonul în desfășurare pentru La Liga nu a putut fi citit")
    assert "not a calendar" in errors[0]
    assert window.standings.season_box.currentText() == "2007/08"
    window.close()


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


def test_a_day_chip_names_the_day_in_two_lines(application):
    today = date(2026, 10, 15)

    assert chip_text(today, today) == "AZI\n15 OCT."
    assert chip_text(date(2026, 10, 16), today) == "MÂINE\n16 OCT."
    assert chip_text(date(2026, 10, 17), today) == "SÂM.\n17 OCT."
    strip = DayStrip()
    chosen = []
    strip.day_chosen.connect(chosen.append)
    strip.show_days(date(2026, 10, 17), today, {date(2026, 10, 17)})
    strip.chips[0].click()
    assert chosen == [date(2026, 10, 14)]
    assert strip.chips[3].isChecked()  # centred again on the chosen day


def test_the_hero_shows_the_league_photo_and_its_credit(application):
    hero = HeroBanner()
    photo = QImage(400, 200, QImage.Format.Format_RGB32)
    photo.fill(QColor("#3355AA"))

    hero.show_league("La Liga", None, photo, "Imagine: DAZN", 0.3)
    hero.resize(1000, hero.height())

    assert hero.photo is photo
    assert hero.credit_label.text() == "Imagine: DAZN"
    assert hero.top == 0.3
    image = hero.grab().toImage()
    assert image.pixelColor(image.width() - 20, image.height() // 2) != image.pixelColor(10, 10)


# --- the colours of the league and a window of any width (Phase 21) ---


def test_choosing_a_league_paints_the_window_in_its_colours(two_league_context):
    window = MainWindow(two_league_context)
    assert current_theme() is THEMES["E0"]
    assert window.styleSheet() == style_sheet(THEMES["E0"])

    window.league_buttons["SP1"].click()

    assert current_theme() is THEMES["SP1"]
    assert window.styleSheet() == style_sheet(THEMES["SP1"])
    assert window.reveal is None  # a window out of sight changes at once
    window.close()


def test_a_window_on_screen_reveals_the_new_colours_with_a_wave(two_league_context):
    window = MainWindow(two_league_context)
    window.show()
    QCoreApplication.processEvents()

    window.league_buttons["SP1"].click()
    first = window.reveal
    assert first is not None and first.isVisible()
    assert first.edge == QColor(THEMES["SP1"].accent)
    assert first.geometry() == window.rect()

    window.league_buttons["E0"].click()  # before the wave has finished
    assert window.reveal is not first and window.reveal is not None
    assert first.isHidden()

    window.reveal.finish()
    assert window.reveal is None
    window.animate = False
    window.league_buttons["SP1"].click()
    assert window.reveal is None
    window.close()


def test_a_narrow_window_keeps_only_the_flags_and_the_mark(window):
    window.fit_width(COMPACT_LOGO_WIDTH - 1)

    assert window.side_panel.width() == COMPACT_SIDE_PANEL_WIDTH
    assert window.side_heading.isHidden() and window.version_note.isHidden()
    assert all(button.compact for button in window.league_buttons.values())
    assert window.lockup.compact

    window.fit_width(COMPACT_WIDTH - 1)  # between the two: flags only, the whole logo
    assert window.side_panel.width() == COMPACT_SIDE_PANEL_WIDTH
    assert not window.lockup.compact

    window.fit_width(COMPACT_WIDTH)
    assert window.side_panel.width() == SIDE_PANEL_WIDTH
    assert not any(button.compact for button in window.league_buttons.values())
    assert window.minimumWidth() <= 1024


@pytest.mark.parametrize("width", [1024, 1280, 1440])
def test_no_screen_scrolls_sideways(window, width):
    window.resize(width, 760)
    window.show()
    for index in range(len(window.pages)):
        window.show_page(index)
        for _ in range(3):
            QCoreApplication.processEvents()
        assert window.scrolls[index].horizontalScrollBar().maximum() == 0, window.pages[index]


def test_a_responsive_box_stacks_its_widgets_when_narrow(application):
    box = ResponsiveBox(500, spacing=10)
    first, side = QWidget(), QWidget()
    box.add(first, stretch=1)
    box.add(side, stretch=0, width=200)

    box.resize(800, 100)
    box.show()
    QCoreApplication.processEvents()
    assert not box.stacked and side.width() == 200
    assert first.geometry().right() < side.geometry().left()

    box.resize(400, 300)
    QCoreApplication.processEvents()
    assert box.stacked
    assert side.geometry().top() > first.geometry().top()
    assert side.width() == first.width()  # the whole width
    assert box.minimumSizeHint().width() <= 400
    box.close()


def test_a_reflow_grid_puts_on_each_row_as_many_widgets_as_fit(application):
    grid = ReflowGrid(200, spacing=10)
    for _ in range(5):
        grid.add(QWidget())

    grid.resize(1100, 100)
    grid.show()
    QCoreApplication.processEvents()
    assert grid.columns == 5

    grid.resize(640, 300)
    QCoreApplication.processEvents()
    assert grid.columns == 3
    rows = sorted({widget.geometry().top() for widget in grid.widgets})
    assert len(rows) == 2

    grid.resize(150, 600)
    QCoreApplication.processEvents()
    assert grid.columns == 1
    grid.close()


def test_a_narrow_match_row_puts_the_probabilities_under_the_teams(window):
    window.matches.show_day(date(2007, 9, 3))
    row = MatchRow(day_rows(window.matches)[0].forecast, ModelName.ELO)

    row.resize(MatchRow.NARROW + 100, MatchRow.HEIGHT)
    row.show()
    QCoreApplication.processEvents()
    assert not row.stacked and row.height() == MatchRow.HEIGHT

    row.resize(MatchRow.NARROW - 100, MatchRow.HEIGHT)
    QCoreApplication.processEvents()
    assert row.stacked and row.height() == MatchRow.STACKED_HEIGHT
    assert not row.grab().isNull()
    row.close()


def test_the_last_match_of_a_league_draws_no_line_across_the_round_corners(window):
    window.matches.show_day(date(2007, 9, 3))
    rows = window.matches.groups[0].rows

    assert rows[-1].last and not any(row.last for row in rows[:-1])


def test_the_hero_keeps_its_subtitle_off_the_image(application):
    hero = HeroBanner()
    hero.show_league("La Liga", None, QImage(1600, 600, QImage.Format.Format_RGB32))
    hero.resize(900, HeroBanner.HEIGHT)
    hero.show()
    QCoreApplication.processEvents()

    image_left = 900 - min(900 * HeroBanner.PHOTO_SHARE, HeroBanner.PHOTO_MAX_WIDTH)
    assert hero.subtitle_label.maximumWidth() <= image_left
    hero.close()


def test_a_hidden_chart_takes_the_new_colours_when_it_is_shown(application):
    view = ChartView()
    figure = Figure()
    figure.add_subplot().plot([0, 1], [0, 1])
    view.show_figure(figure)

    draws = []
    figure.canvas.mpl_connect("draw_event", lambda event: draws.append(event))

    view.restyle()  # out of sight: not redrawn yet
    QCoreApplication.processEvents()
    assert draws == []

    view.show()
    for _ in range(3):
        QCoreApplication.processEvents()
    assert draws
    view.close()
