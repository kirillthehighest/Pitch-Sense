"""Clasament: a league's table with the clubs' crests and their last five results, at the end of
a season (or so far, for the season in progress) or on any day of it."""

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QDate
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from app.data.preprocessing import season_date_window
from app.services.formatting import date_text, season_text
from app.services.registry import LeagueServices
from app.services.teams import StandingRow
from app.statistics.team_statistics import TeamResult
from app.ui.brand import team_badge
from app.ui.context import AppContext
from app.ui.widgets import FormStrip, card, fill_table, label, make_table

HEADERS = ["Loc", "Echipă", "M", "V", "E", "Î", "GM", "GP", "Dif.", "Pct.", "Ultimele 5"]
FORM_COLUMN = HEADERS.index("Ultimele 5")
ICON_SIZE = 26


@dataclass(frozen=True, eq=False)
class TableAnswer:
    """A table and every team's form on the same day."""

    season: str
    rows: list[StandingRow]
    forms: dict[str, tuple[TeamResult, ...]]
    whole_season: bool


def difference_text(difference: int) -> str:
    return f"{difference:+d}".replace("-", "−") if difference else "0"


class StandingsPage(QWidget):
    """Choose a season and, if wanted, a day; a click on a team opens its page."""

    title = "Clasament"
    subtitle = "Clasamentul ligii, cu forma fiecărei echipe; la final de sezon sau la orice dată."

    def __init__(self, context: AppContext, open_team: Callable[..., None]) -> None:
        super().__init__()
        self._context = context
        self._open_team = open_team
        self._league: LeagueServices | None = None
        self.answer: TableAnswer | None = None
        self.season_box = QComboBox()
        self.season_box.currentIndexChanged.connect(self._season_changed)
        self.whole_season_box = QCheckBox("Tot sezonul")
        self.whole_season_box.setChecked(True)
        self.whole_season_box.toggled.connect(self._whole_season_toggled)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setEnabled(False)
        self.date_edit.dateChanged.connect(self.refresh)
        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.addWidget(label("Sezon", "caption"))
        controls.addWidget(self.season_box)
        controls.addSpacing(12)
        controls.addWidget(label("Meciuri până la", "caption"))
        controls.addWidget(self.whole_season_box)
        controls.addWidget(self.date_edit)
        controls.addStretch()
        self.caption = label(role="caption", wrap=True)
        table_card, table_layout = card()
        self.title_label = label(role="section")
        table_layout.addWidget(self.title_label)
        self.table = make_table(HEADERS, stretch_column=1)
        self.table.cellClicked.connect(self._clicked)
        table_layout.addWidget(self.table)
        table_layout.addWidget(self.caption)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addLayout(controls)
        layout.addWidget(table_card)
        layout.addStretch()

    def show_league(self, league: LeagueServices) -> None:
        self._league = league
        self.season_box.blockSignals(True)
        self.season_box.clear()
        for season in reversed(league.catalog.seasons()):
            self.season_box.addItem(season_text(season), season)
        self.season_box.blockSignals(False)
        self._season_changed()

    def show_season(self, season: str) -> None:
        self.season_box.setCurrentIndex(self.season_box.findData(season))

    def refresh(self) -> None:
        """Compute the table of the chosen season and day in the background."""
        if self._league is None or self.season_box.currentData() is None:
            return
        season = self.season_box.currentData()
        whole = self.whole_season_box.isChecked()
        teams = self._league.teams
        before = None if whole else self.date_edit.date().toPython()

        def answer() -> TableAnswer:
            rows = teams.standings(season, before)
            day = before or teams.season_end(season)
            return TableAnswer(
                season, rows, {row.team: teams.form(row.team, day) for row in rows}, whole
            )

        self._context.run_task(answer, self._show, self._context.report_error)

    def _show(self, answer: TableAnswer) -> None:
        self.answer = answer
        favourite = self._context.preferences.favourite
        favourite_team = favourite.team if favourite else None
        rows = answer.rows
        fill_table(
            self.table,
            [
                [
                    str(row.position),
                    row.team,
                    *(
                        str(value)
                        for value in (
                            row.record.played,
                            row.record.wins,
                            row.record.draws,
                            row.record.losses,
                            row.record.goals_for,
                            row.record.goals_against,
                        )
                    ),
                    difference_text(row.record.goal_difference),
                    str(row.record.points),
                    "",
                ]
                for row in rows
            ],
            highlight={i for i, row in enumerate(rows) if row.team == favourite_team},
            icons=[
                QIcon(team_badge(row.team, ICON_SIZE, highlighted=row.team == favourite_team))
                for row in rows
            ],
            icon_column=1,
        )
        for index, row in enumerate(rows):
            strip = FormStrip()
            strip.set_results([result.value for result in answer.forms[row.team]])
            holder = QWidget()
            holder_layout = QHBoxLayout(holder)
            holder_layout.setContentsMargins(8, 0, 8, 0)
            holder_layout.addWidget(strip)
            holder_layout.addStretch()
            self.table.setCellWidget(index, FORM_COLUMN, holder)
        self.table.setFixedHeight(
            self.table.horizontalHeader().sizeHint().height()
            + self.table.verticalHeader().defaultSectionSize() * len(rows)
            + 2 * self.table.frameWidth()
        )
        name = self._league.name
        when = (
            "tot sezonul"
            if answer.whole_season
            else f"înainte de {date_text(self.date_edit.date().toPython())}"
        )
        if answer.whole_season and answer.season == self._league.catalog.current_season:
            when = "până acum (sezon în desfășurare)"
        self.title_label.setText(f"{name} {season_text(answer.season)} · {when}")
        self.caption.setText(
            "M meciuri, V victorii, E egaluri, Î înfrângeri, GM goluri marcate, GP goluri primite. "
            "La egalitate de puncte decid golaverajul, apoi golurile marcate; deducerile de puncte "
            "nu sunt incluse. Apasă pe o echipă ca să-i deschizi pagina."
        )

    def _clicked(self, row: int, _column: int) -> None:
        if self.answer is not None and 0 <= row < len(self.answer.rows):
            self._open_team(self._league.code, self.answer.rows[row].team, self.answer.season)

    def _whole_season_toggled(self, checked: bool) -> None:
        self.date_edit.setEnabled(not checked)
        self.refresh()

    def _season_changed(self) -> None:
        season = self.season_box.currentData()
        if season is None or self._league is None:
            return
        first_day, last_day = season_date_window(season)
        matches = self._league.catalog.season_matches(season)
        self.date_edit.blockSignals(True)
        self.date_edit.setDateRange(_qdate(first_day), _qdate(last_day))
        self.date_edit.setDate(_qdate(matches[len(matches) // 2].match_date))
        self.date_edit.blockSignals(False)
        self.refresh()


def _qdate(day) -> QDate:
    return QDate(day.year, day.month, day.day)
