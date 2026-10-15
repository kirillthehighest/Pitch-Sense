"""Meciuri: the first screen (Phase 19). The matches of a day in every league, each with the
chosen model's probabilities; played days show the result and whether the model got it right.

A click on a match opens its page (``match_detail.py``). The right column follows "your team"
and the chosen league's table.
"""

from collections.abc import Callable
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.data.competitions import competition
from app.prediction.outputs import ModelName
from app.services.formatting import day_name, season_text, short_date_text
from app.services.labels import country_label, model_label
from app.services.predictions import MatchForecast
from app.ui.brand import flag_pixmap, team_badge
from app.ui.context import AppContext, LeagueServices
from app.ui.match_detail import HypotheticalDialog, MatchDetail
from app.ui.match_widgets import DayStrip, MatchRow, ProbabilityHeading
from app.ui.widgets import FormStrip, card, label

# The model shown in the list unless the user picks another: over the five leagues together,
# logistic regression has the lowest Brier score, really ahead of Elo and Poisson (docs/leagues.md).
DEFAULT_MODEL = ModelName.LOGISTIC_REGRESSION
SIDE_WIDTH = 360
TABLE_ROWS = 6
PREPARING = "Se pregătesc predicțiile…"
NO_MATCHES = "Nu sunt meciuri în această zi."


def next_match_day(days: list[date], today: date) -> date:
    """The first day with matches from ``today`` on; the last one when the season is over."""
    return next((day for day in days if day >= today), days[-1] if days else today)


class LeagueGroup(QFrame):
    """One league's matches of the day: a heading with the flag, then one row per match."""

    def __init__(self, code: str, open_standings: Callable[[str], None]) -> None:
        super().__init__()
        self.code = code
        self.setProperty("role", "list")
        head = QFrame()
        head.setProperty("role", "list-head")
        flag = QLabel()
        flag.setPixmap(flag_pixmap(code, 20))
        name = label(competition(code).name.upper(), "strong")
        country = label(country_label(code), "caption")
        self.standings_button = QPushButton("Clasament ›")
        self.standings_button.setProperty("role", "link")
        self.standings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.standings_button.clicked.connect(lambda: open_standings(code))
        heading = QHBoxLayout(head)
        heading.setContentsMargins(16, 10, 12, 10)
        heading.setSpacing(10)
        heading.addWidget(flag)
        heading.addWidget(name)
        heading.addWidget(country)
        heading.addStretch()
        heading.addWidget(self.standings_button)
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        self.note = label(role="caption", wrap=True)
        self.note.setContentsMargins(16, 12, 16, 14)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(head)
        layout.addLayout(self.rows_layout)
        layout.addWidget(self.note)
        self.rows: list[MatchRow] = []

    def show_rows(self, rows: list[MatchRow]) -> None:
        self.rows = rows
        for row in rows:
            self.rows_layout.addWidget(row)
        self.note.setVisible(False)

    def show_note(self, text: str) -> None:
        self.note.setText(text)
        self.note.setVisible(True)


class MatchesPage(QWidget):
    """The day's matches of every league; the chosen league comes first."""

    title = "Meciuri"
    subtitle = (
        "Meciurile fiecărei zile, cu predicțiile modelelor. Fiecare predicție folosește doar "
        "meciurile jucate înaintea ei."
    )

    def __init__(
        self,
        context: AppContext,
        open_standings: Callable[[str], None],
        open_team: Callable[..., None],
        choose_favourite: Callable[[], None],
    ) -> None:
        super().__init__()
        self._context = context
        self._open_standings = open_standings
        self._open_team = open_team
        self._league: LeagueServices | None = None
        self.day: date | None = None
        self.groups: list[LeagueGroup] = []

        self.day_strip = DayStrip()
        self.day_strip.day_chosen.connect(self.show_day)
        self.model_box = QComboBox()
        for model in ModelName:
            self.model_box.addItem(model_label(str(model)), model)
        self.model_box.setCurrentIndex(self.model_box.findData(DEFAULT_MODEL))
        self.model_box.setToolTip(
            "Modelul ale cărui probabilități apar în listă. Implicit: regresia logistică, cu cel "
            "mai mic scor Brier pe cele cinci ligi (ecranul Analiză)."
        )
        self.model_box.currentIndexChanged.connect(self.refresh)
        self.all_button = QPushButton("Toate ligile")
        self.league_button = QPushButton()
        filters = QButtonGroup(self)
        for button in (self.all_button, self.league_button):
            button.setProperty("role", "filter")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(self.refresh)
            filters.addButton(button)
        self.all_button.setChecked(True)
        self.hypothetical_button = QPushButton("Alt meci…")
        self.hypothetical_button.setToolTip(
            "Predicția pentru oricare două echipe ale unui sezon, la o dată aleasă"
        )
        self.hypothetical_button.clicked.connect(self.open_hypothetical)
        self.day_label = label(role="section")

        controls = QHBoxLayout()
        controls.setSpacing(10)
        controls.addWidget(self.day_label)
        controls.addStretch()
        controls.addWidget(self.all_button)
        controls.addWidget(self.league_button)
        controls.addSpacing(10)
        controls.addWidget(label("Model", "caption"))
        controls.addWidget(self.model_box)
        controls.addWidget(self.hypothetical_button)

        self.groups_layout = QVBoxLayout()
        self.groups_layout.setSpacing(16)
        self.empty_label = label(NO_MATCHES, "caption")
        self.legend = label(
            "Probabilitățile modelului ales; cea mai mare este colorată. La meciurile jucate, "
            "bifa verde arată că rezultatul cel mai probabil s-a întâmplat, crucea roșie că nu.",
            "caption",
            wrap=True,
        )
        listing = QVBoxLayout()
        listing.setSpacing(14)
        listing.addWidget(self.day_strip)
        listing.addLayout(controls)
        listing.addWidget(self.legend)
        listing.addWidget(ProbabilityHeading())
        listing.addWidget(self.empty_label)
        listing.addLayout(self.groups_layout)
        listing.addStretch()

        side = QVBoxLayout()
        side.setSpacing(16)
        side.addWidget(self._favourite_card(choose_favourite))
        side.addWidget(self._table_card())
        side.addStretch()
        side_widget = QWidget()
        side_widget.setLayout(side)
        side_widget.setFixedWidth(SIDE_WIDTH)

        list_page = QWidget()
        columns = QHBoxLayout(list_page)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(20)
        columns.addLayout(listing, stretch=1)
        columns.addWidget(side_widget, alignment=Qt.AlignmentFlag.AlignTop)

        self.detail = MatchDetail(context, open_team)
        self.detail.back_button.clicked.connect(self.show_list)
        self.views = QStackedWidget()
        self.views.addWidget(list_page)
        self.views.addWidget(self.detail)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.views)

    @property
    def model(self) -> ModelName:
        return ModelName(self.model_box.currentData())

    def show_league(self, league: LeagueServices) -> None:
        self._league = league
        self.league_button.setText(f"Doar {league.name}")
        self.refresh()

    def show_list(self) -> None:
        self.views.setCurrentIndex(0)

    def show_match(self, forecast: MatchForecast) -> None:
        """Open a match's page."""
        self.detail.show_forecast(forecast)
        self.views.setCurrentIndex(1)

    def show_day(self, day: date) -> None:
        self.day = day
        self.refresh()

    def open_hypothetical(self) -> HypotheticalDialog:
        """Ask for any two teams of a season and a date; open the prediction as a match page."""
        dialog = HypotheticalDialog(self._context, self._league, self)
        dialog.predicted.connect(self.show_match)
        dialog.open()
        return dialog

    def league_ready(self, code: str) -> None:
        """A league's predictions are ready: show its matches."""
        if self.views.currentIndex() == 0:
            self.refresh()

    def refresh(self) -> None:
        """Show the chosen day's matches of every league whose predictions are ready."""
        if self._league is None:
            return
        ready = self._ready_leagues()
        if self.day is None and ready:
            days = sorted({day for league in ready for day in league.predictions.match_days()})
            self.day = next_match_day(days, self._context.today())
        day = self.day or self._context.today()
        all_days = {d for league in ready for d in league.predictions.match_days()}
        self.day_strip.show_days(day, self._context.today(), all_days)
        name, date_name = day_name(day, self._context.today()), short_date_text(day)
        self.day_label.setText(
            (date_name if name == date_name else f"{name} · {date_name}").upper()
        )
        for group in self.groups:
            group.setParent(None)
            group.deleteLater()
        self.groups = []
        codes = [self._league.code] + [
            c for c in self._context.competitions if c != self._league.code
        ]
        if self.league_button.isChecked():
            codes = [self._league.code]
        favourite = self._favourite_team()
        for code in codes:
            group = LeagueGroup(code, self._open_standings)
            league = self._context.league(code)
            if not league.predictions.is_prepared:
                group.show_note(PREPARING)
            else:
                forecasts = league.predictions.on_day(day)
                if not forecasts:
                    group.deleteLater()
                    continue
                rows = []
                for forecast in forecasts:
                    row = MatchRow(forecast, self.model, favourite)
                    row.clicked.connect(lambda _, f=forecast: self.show_match(f))
                    rows.append(row)
                group.show_rows(rows)
            self.groups.append(group)
            self.groups_layout.addWidget(group)
        self.empty_label.setVisible(not self.groups)
        self.show_favourite()
        self._show_table()

    def show_favourite(self) -> None:
        """The card of "your team": its next match and its last results."""
        favourite = self._context.preferences.favourite
        self.favourite_rows_widget.hide()
        for row in self.favourite_rows:
            row.setParent(None)
            row.deleteLater()
        self.favourite_rows = []
        self.favourite_open_button.setVisible(False)
        if favourite is None or favourite.competition not in self._context.competitions:
            self.favourite_badge.clear()
            self.favourite_name.setText("Alege echipa pe care o urmărești")
            self.favourite_caption.setText("Meciurile ei vor fi evidențiate în listă.")
            self.favourite_form.set_results(())
            self.favourite_choose_button.show()
            return
        self.favourite_choose_button.hide()
        league = self._context.league(favourite.competition)
        season = league.catalog.seasons()[-1]
        self.favourite_badge.setPixmap(team_badge(favourite.team, 52, highlighted=True))
        self.favourite_name.setText(favourite.team.upper())
        self.favourite_caption.setText(f"{league.name} · {season_text(season)}")
        if not league.predictions.is_prepared:
            self.favourite_form.set_results(())
            return
        matches = league.predictions.team_matches(favourite.team, season)
        played = [m for m in matches if m.played is not None]
        self.favourite_form.set_results([_result_code(m, favourite.team) for m in played[-5:]])
        upcoming = [m for m in matches if m.played is None]
        for forecast in upcoming[:1] + played[-1:][::-1]:
            row = MatchRow(forecast, self.model, favourite.team, show_date=True, stacked=True)
            row.clicked.connect(lambda _, f=forecast: self.show_match(f))
            self.favourite_rows.append(row)
            self.favourite_rows_layout.addWidget(row)
        self.favourite_rows_widget.setVisible(bool(self.favourite_rows))
        self.favourite_open_button.setVisible(True)

    def _favourite_card(self, choose_favourite: Callable[[], None]) -> QFrame:
        frame, layout = card(role="favourite")
        layout.addWidget(label("ECHIPA TA", "eyebrow"))
        self.favourite_badge = QLabel()
        self.favourite_name = label(role="team", wrap=True)
        self.favourite_caption = label(role="caption", wrap=True)
        identity = QHBoxLayout()
        identity.setSpacing(12)
        identity.addWidget(self.favourite_badge)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(self.favourite_name)
        names.addWidget(self.favourite_caption)
        identity.addLayout(names, stretch=1)
        layout.addLayout(identity)
        self.favourite_form = FormStrip()
        layout.addWidget(self.favourite_form)
        self.favourite_rows: list[MatchRow] = []
        self.favourite_rows_widget = QWidget()
        self.favourite_rows_layout = QVBoxLayout(self.favourite_rows_widget)
        self.favourite_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.favourite_rows_layout.setSpacing(0)
        layout.addWidget(self.favourite_rows_widget)
        self.favourite_choose_button = QPushButton("Alege echipa ta")
        self.favourite_choose_button.clicked.connect(choose_favourite)
        layout.addWidget(self.favourite_choose_button)
        self.favourite_open_button = QPushButton("Pagina echipei ›")
        self.favourite_open_button.setProperty("role", "link")
        self.favourite_open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.favourite_open_button.clicked.connect(self._open_favourite)
        self.favourite_open_button.hide()
        layout.addWidget(self.favourite_open_button, alignment=Qt.AlignmentFlag.AlignLeft)
        frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        return frame

    def _table_card(self) -> QFrame:
        frame, layout = card()
        self.table_title = label(role="section")
        layout.addWidget(self.table_title)
        self.table_rows_layout = QVBoxLayout()
        self.table_rows_layout.setSpacing(6)
        layout.addLayout(self.table_rows_layout)
        self.table_button = QPushButton("Tot clasamentul ›")
        self.table_button.setProperty("role", "link")
        self.table_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.table_button.clicked.connect(lambda: self._open_standings(self._league.code))
        layout.addWidget(self.table_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.table_labels: list[QWidget] = []
        frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        return frame

    def _show_table(self) -> None:
        """The top of the chosen league's latest table."""
        for widget in self.table_labels:
            widget.setParent(None)
            widget.deleteLater()
        self.table_labels = []
        league = self._league
        season = league.catalog.seasons()[-1]
        self.table_title.setText(f"{league.name} {season_text(season)}".upper())
        favourite = self._favourite_team()
        for row in league.teams.standings(season)[:TABLE_ROWS]:
            line = QWidget()
            line_layout = QHBoxLayout(line)
            line_layout.setContentsMargins(0, 0, 0, 0)
            line_layout.setSpacing(8)
            badge = QLabel()
            badge.setPixmap(team_badge(row.team, 20, highlighted=row.team == favourite))
            line_layout.addWidget(label(str(row.position), "caption"))
            line_layout.addWidget(badge)
            name = label(row.team, "strong" if row.team == favourite else None)
            line_layout.addWidget(name, stretch=1)
            line_layout.addWidget(label(str(row.record.played), "caption"))
            line_layout.addWidget(label(str(row.record.points), "strong"))
            self.table_labels.append(line)
            self.table_rows_layout.addWidget(line)

    def _ready_leagues(self) -> list[LeagueServices]:
        leagues = [self._context.league(code) for code in self._context.competitions]
        return [league for league in leagues if league.predictions.is_prepared]

    def _favourite_team(self) -> str | None:
        favourite = self._context.preferences.favourite
        return favourite.team if favourite else None

    def _open_favourite(self) -> None:
        favourite = self._context.preferences.favourite
        if favourite is not None:
            self._open_team(favourite.competition, favourite.team)


def _result_code(forecast: MatchForecast, team: str) -> str:
    """W, D or L for ``team`` in a played match."""
    played = forecast.played
    scored, conceded = (
        (played.home_goals, played.away_goals)
        if team == played.home_team
        else (played.away_goals, played.home_goals)
    )
    return "W" if scored > conceded else "L" if scored < conceded else "D"
