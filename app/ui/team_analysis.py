"""Team Analysis: the league table and one team's season, as of a chosen date."""

from dataclasses import dataclass

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.data.preprocessing import season_date_window
from app.services.teams import RatingSeason, SeasonGroups, StandingRow, TeamOverview
from app.statistics.team_statistics import TeamStatistics
from app.ui.context import AppContext
from app.ui.widgets import ChartView, fill_table, make_table, number
from app.visualization.charts import elo_history_chart, team_groups_chart

TABLE_HEADERS = ["Pos", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]
VIEWS = ("League table", "Elo rating", "Team groups")
GROUPS_NEED_WHOLE_SEASON = (
    'Team groups describe a finished season. Tick "Whole season" to see them.'
)


@dataclass(frozen=True, eq=False)
class TeamAnswer:
    """Everything the tab shows for one team and season."""

    standings: list[StandingRow]
    overview: TeamOverview
    elo_history: tuple[RatingSeason, ...]
    groups: SeasonGroups | None  # only for the whole season


def record_text(record: TeamStatistics) -> str:
    return (
        f"{record.played} played: {record.wins} W, {record.draws} D, {record.losses} L, "
        f"goals {record.goals_for}-{record.goals_against}, {record.points} points"
    )


class TeamAnalysisTab(QWidget):
    """Choose a season, a team and a date; show the table and the team's overview."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context

        self.season_box = QComboBox()
        self.season_box.addItems(list(reversed(context.catalog.seasons())))
        self.season_box.currentTextChanged.connect(self._season_changed)
        self.team_box = QComboBox()
        self.whole_season_box = QCheckBox("Whole season")
        self.whole_season_box.setChecked(True)
        self.whole_season_box.toggled.connect(
            lambda checked: self.date_edit.setEnabled(not checked)
        )
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setEnabled(False)
        self.show_button = QPushButton("Show")
        self.show_button.clicked.connect(self.show_team)

        choice = QFormLayout()
        choice.addRow("Season", self.season_box)
        choice.addRow("Team", self.team_box)
        as_of = QHBoxLayout()
        as_of.addWidget(self.whole_season_box)
        as_of.addWidget(self.date_edit)
        choice.addRow("Matches before", as_of)

        self.standings_table = make_table(TABLE_HEADERS, stretch_column=1)
        self.elo_chart = ChartView("The team's Elo rating appears here.")
        self.groups_chart = ChartView("The season's team groups appear here.")
        self.views = QTabWidget()
        for name, widget in zip(
            VIEWS, (self.standings_table, self.elo_chart, self.groups_chart), strict=True
        ):
            self.views.addTab(widget, name)
        overview_box = QGroupBox("Team overview")
        self.overview_form = QFormLayout(overview_box)
        self.overview_labels = {
            name: QLabel()
            for name in (
                "Position",
                "Season record",
                "At home",
                "Away",
                "Last 5 results",
                "Shots on target per match",
                "Pre-season group",
                "Season group",
            )
        }
        for name, label in self.overview_labels.items():
            label.setWordWrap(True)
            self.overview_form.addRow(name, label)
        note = QLabel(
            "Groups come from K-Means on six per-match season indicators. The pre-season group "
            "uses the previous season; the season group describes the finished season. Ties in "
            "the table are broken by goal difference, then goals scored."
        )
        note.setWordWrap(True)

        results = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(overview_box)
        left.addWidget(note)
        left.addStretch()
        results.addLayout(left, stretch=2)
        results.addWidget(self.views, stretch=3)

        layout = QVBoxLayout(self)
        layout.addLayout(choice)
        layout.addWidget(self.show_button)
        layout.addLayout(results)

        self._season_changed(self.season_box.currentText())

    def show_team(self) -> None:
        """Compute the table and the overview in the background."""
        season, team = self.season_box.currentText(), self.team_box.currentText()
        before = None if self.whole_season_box.isChecked() else self.date_edit.date().toPython()
        teams = self._context.teams
        self.show_button.setEnabled(False)
        self._context.run_task(
            lambda: TeamAnswer(
                standings=teams.standings(season, before),
                overview=teams.overview(season, team, before),
                elo_history=teams.elo_history(team),
                groups=teams.season_groups(season) if before is None else None,
            ),
            self._show,
            self._failed,
        )

    def _show(self, answer: TeamAnswer) -> None:
        standings, overview = answer.standings, answer.overview
        self.show_button.setEnabled(True)
        fill_table(
            self.standings_table,
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
                            row.record.goal_difference,
                            row.record.points,
                        )
                    ),
                ]
                for row in standings
            ],
        )
        shots = overview.match_statistics
        texts = {
            "Position": f"{overview.position} of {len(standings)}",
            "Season record": record_text(overview.record),
            "At home": record_text(overview.home),
            "Away": record_text(overview.away),
            "Last 5 results": " ".join(outcome.value for outcome in overview.form) or "-",
            "Shots on target per match": (
                f"{number(shots.shots_on_target, 2)} for, "
                f"{number(shots.opponent_shots_on_target, 2)} against"
            ),
            "Pre-season group": overview.pre_season_group,
            "Season group": overview.season_group or "Season not finished at this date",
        }
        for name, text in texts.items():
            self.overview_labels[name].setText(text)
        whole_season = answer.groups is not None
        self.elo_chart.show_figure(
            elo_history_chart(
                overview.team,
                answer.elo_history,
                season=overview.season,
                marked_date=None if whole_season else overview.before,
            )
        )
        if answer.groups is None:
            self.groups_chart.show_message(GROUPS_NEED_WHOLE_SEASON)
        else:
            self.groups_chart.show_figure(team_groups_chart(answer.groups, team=overview.team))

    def _failed(self, message: str) -> None:
        self.show_button.setEnabled(True)
        self._context.report_error(message)

    def _season_changed(self, season: str) -> None:
        if not season:
            return
        self.team_box.clear()
        self.team_box.addItems(self._context.catalog.teams(season))
        first_day, last_day = season_date_window(season)
        self.date_edit.setDateRange(_qdate(first_day), _qdate(last_day))
        matches = self._context.catalog.season_matches(season)
        self.date_edit.setDate(_qdate(matches[len(matches) // 2].match_date))


def _qdate(day) -> QDate:
    return QDate(day.year, day.month, day.day)
