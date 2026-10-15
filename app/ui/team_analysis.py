"""Echipe: the league table and one team's season, as of a chosen date, with its charts."""

from dataclasses import dataclass

from PySide6.QtCore import QDate
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.data.preprocessing import season_date_window
from app.services.formatting import date_text, number, quantity, season_text
from app.services.teams import RatingSeason, SeasonGroups, StandingRow, TeamOverview
from app.statistics.team_statistics import TeamStatistics
from app.ui.brand import team_badge
from app.ui.context import AppContext, LeagueServices
from app.ui.widgets import (
    ChartView,
    FormStrip,
    PageTabs,
    card,
    fill_table,
    label,
    make_table,
)
from app.visualization.charts import elo_history_chart, team_groups_chart

TABLE_HEADERS = ["Loc", "Echipă", "M", "V", "E", "Î", "GM", "GP", "Dif.", "Pct."]
VIEWS = ("Clasament", "Rating Elo", "Grupuri")
OVERVIEW_ROWS = (
    "Poziție",
    "Sezon",
    "Acasă",
    "În deplasare",
    "Ultimele 5",
    "Șuturi pe poartă pe meci",
    "Grupul de dinaintea sezonului",
    "Grupul sezonului",
)
GROUPS_NEED_WHOLE_SEASON = (
    "Grupurile descriu un sezon încheiat. Bifează „Tot sezonul” ca să le vezi."
)
GROUPS_IN_PROGRESS = (
    "Sezonul este în desfășurare. Grupurile K‑Means descriu sezoane încheiate, așa că apar după "
    "ultimul meci al sezonului."
)
GROUPS_NO_STATISTICS = "Sezonul nu are statistici de șuturi, deci echipele nu pot fi grupate."
SEASON_NOT_FINISHED = "Sezonul nu este încheiat la această dată"
FORM = "Ultimele 5"
BADGE_SIZE = 64
ICON_SIZE = 26
CHART_HEIGHT = 540  # room for the names of twenty teams on the groups chart


@dataclass(frozen=True, eq=False)
class TeamAnswer:
    """Everything the screen shows for one team and season."""

    standings: list[StandingRow]
    overview: TeamOverview
    elo_history: tuple[RatingSeason, ...]
    whole_season: bool  # every match of the season (so far, for the season in progress)
    groups: SeasonGroups | None  # only for the whole of a completed season
    groups_problem: str | None  # why there are no groups for the whole season


def record_text(record: TeamStatistics) -> str:
    return (
        f"{quantity(record.played, 'meci', 'meciuri')}: {record.wins} V, {record.draws} E, "
        f"{record.losses} Î; goluri {record.goals_for}–{record.goals_against}; "
        f"{quantity(record.points, 'punct', 'puncte')}"
    )


class TeamAnalysisTab(QWidget):
    """Choose a season, a team and a date; show the table, the team's profile and charts."""

    title = "Echipe"
    subtitle = "Clasamentul la orice dată, profilul unei echipe, ratingul ei Elo și grupurile."

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self._league: LeagueServices | None = None

        self.season_box = QComboBox()
        self.season_box.currentIndexChanged.connect(self._season_changed)
        self.team_box = QComboBox()
        self.whole_season_box = QCheckBox("Tot sezonul")
        self.whole_season_box.setChecked(True)
        self.whole_season_box.toggled.connect(
            lambda checked: self.date_edit.setEnabled(not checked)
        )
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setEnabled(False)
        self.show_button = QPushButton("Arată")
        self.show_button.setProperty("role", "primary")
        self.show_button.clicked.connect(self.show_team)

        choice_card, choice_layout = card()
        choice = QHBoxLayout()
        choice.setSpacing(12)
        for text, widget in (("Sezon", self.season_box), ("Echipă", self.team_box)):
            choice.addWidget(label(text, "caption"))
            choice.addWidget(widget, stretch=1)
        choice.addWidget(label("Meciuri până la", "caption"))
        choice.addWidget(self.whole_season_box)
        choice.addWidget(self.date_edit)
        choice.addWidget(self.show_button)
        choice_layout.addLayout(choice)

        overview_card, overview_layout = card("Profilul echipei")
        self.team_badge = QLabel()
        self.team_label = label(role="hero", wrap=True)
        identity = QHBoxLayout()
        identity.setSpacing(16)
        identity.addWidget(self.team_badge)
        identity.addWidget(self.team_label, stretch=1)
        overview_layout.addLayout(identity)
        self.overview_form = QFormLayout()
        self.overview_form.setSpacing(9)
        self.overview_labels = {name: label(wrap=True) for name in OVERVIEW_ROWS if name != FORM}
        self.form_strip = FormStrip()
        for name in OVERVIEW_ROWS:
            widget = self.form_strip if name == FORM else self.overview_labels[name]
            self.overview_form.addRow(label(name, "caption"), widget)
        overview_layout.addLayout(self.overview_form)
        overview_layout.addWidget(
            label(
                "Grupurile vin din K‑Means pe șase valori pe meci ale unui sezon. Grupul de "
                "dinaintea sezonului folosește sezonul anterior; grupul sezonului descrie sezonul "
                "încheiat. La egalitate de puncte, clasamentul folosește golaverajul, apoi "
                "golurile marcate; deducerile de puncte nu sunt incluse.",
                "caption",
                wrap=True,
            )
        )
        overview_layout.addStretch()

        self.standings_table = make_table(TABLE_HEADERS, stretch_column=1)
        self.elo_chart = ChartView("Ratingul Elo al echipei apare aici.")
        self.groups_chart = ChartView("Grupurile echipelor din sezon apar aici.")
        for chart in (self.elo_chart, self.groups_chart):
            chart.setMinimumHeight(CHART_HEIGHT)
        views_card, views_layout = card()
        self.views = PageTabs()
        for name, widget in zip(
            VIEWS, (self.standings_table, self.elo_chart, self.groups_chart), strict=True
        ):
            self.views.addTab(widget, name)
        views_layout.addWidget(self.views)

        results = QHBoxLayout()
        results.setSpacing(16)
        results.addWidget(overview_card, stretch=2)
        results.addWidget(views_card, stretch=3)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(choice_card)
        layout.addLayout(results, stretch=1)

    def show_league(self, league: LeagueServices) -> None:
        self._league = league
        self.season_box.blockSignals(True)
        self.season_box.clear()
        for season in reversed(league.catalog.seasons()):
            self.season_box.addItem(season_text(season), season)
        self.season_box.blockSignals(False)
        self._season_changed()
        self.team_label.clear()
        self.team_badge.clear()
        self.form_strip.set_results(())
        for widget in self.overview_labels.values():
            widget.clear()
        fill_table(self.standings_table, [])
        self.elo_chart.show_message("Ratingul Elo al echipei apare aici.")
        self.groups_chart.show_message("Grupurile echipelor din sezon apar aici.")

    def show_team(self) -> None:
        """Compute the table, the profile and the charts' data in the background."""
        season, team = self.season_box.currentData(), self.team_box.currentText()
        before = None if self.whole_season_box.isChecked() else self.date_edit.date().toPython()
        teams = self._league.teams
        self.show_button.setEnabled(False)

        def answer() -> TeamAnswer:
            groups, problem = None, None
            if before is None and season == teams.in_progress:
                problem = GROUPS_IN_PROGRESS
            elif before is None:
                try:
                    groups = teams.season_groups(season)
                except ValueError:  # a season without shot statistics has no groups
                    problem = GROUPS_NO_STATISTICS
            return TeamAnswer(
                whole_season=before is None,
                standings=teams.standings(season, before),
                overview=teams.overview(season, team, before),
                elo_history=teams.elo_history(team),
                groups=groups,
                groups_problem=problem,
            )

        self._context.run_task(answer, self._show, self._failed)

    def _show(self, answer: TeamAnswer) -> None:
        standings, overview = answer.standings, answer.overview
        self.show_button.setEnabled(True)
        favourite = self._favourite()
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
                        )
                    ),
                    f"{row.record.goal_difference:+d}".replace("-", "−")
                    if row.record.goal_difference
                    else "0",
                    str(row.record.points),
                ]
                for row in standings
            ],
            highlight={
                i for i, row in enumerate(standings) if row.team in (favourite, overview.team)
            },
            icons=[
                QIcon(team_badge(row.team, ICON_SIZE, highlighted=row.team == favourite))
                for row in standings
            ],
            icon_column=1,
        )
        shots = overview.match_statistics
        whole = answer.whole_season
        self.team_label.setText(overview.team.upper())
        self.team_badge.setPixmap(
            team_badge(overview.team, BADGE_SIZE, highlighted=overview.team == favourite)
        )
        self.form_strip.set_results([result.value for result in overview.form])
        texts = {
            "Poziție": f"locul {overview.position} din {len(standings)}"
            + ("" if whole else f", înainte de {date_text(overview.before)}"),
            "Sezon": record_text(overview.record),
            "Acasă": record_text(overview.home),
            "În deplasare": record_text(overview.away),
            "Șuturi pe poartă pe meci": (
                f"{number(shots.shots_on_target, 2)} ale echipei, "
                f"{number(shots.opponent_shots_on_target, 2)} ale adversarilor"
            ),
            "Grupul de dinaintea sezonului": overview.pre_season_group,
            "Grupul sezonului": overview.season_group or SEASON_NOT_FINISHED,
        }
        for name, text in texts.items():
            self.overview_labels[name].setText(text)
        self.elo_chart.show_figure(
            elo_history_chart(
                overview.team,
                answer.elo_history,
                season=overview.season,
                marked_date=None if whole else overview.before,
            )
        )
        if answer.groups is not None:
            self.groups_chart.show_figure(team_groups_chart(answer.groups, team=overview.team))
        elif answer.groups_problem is not None:
            self.groups_chart.show_message(answer.groups_problem)
        else:
            self.groups_chart.show_message(GROUPS_NEED_WHOLE_SEASON)

    def _failed(self, message: str) -> None:
        self.show_button.setEnabled(True)
        self._context.report_error(message)

    def _favourite(self) -> str | None:
        favourite = self._context.preferences.favourite
        if favourite and self._league and favourite.competition == self._league.code:
            return favourite.team
        return None

    def _season_changed(self) -> None:
        season = self.season_box.currentData()
        if season is None or self._league is None:
            return
        catalog = self._league.catalog
        teams = catalog.teams(season)
        self.team_box.clear()
        self.team_box.addItems(teams)
        favourite = self._favourite()
        if favourite in teams:
            self.team_box.setCurrentText(favourite)
        first_day, last_day = season_date_window(season)
        self.date_edit.setDateRange(_qdate(first_day), _qdate(last_day))
        matches = catalog.season_matches(season)
        self.date_edit.setDate(_qdate(matches[len(matches) // 2].match_date))


def _qdate(day) -> QDate:
    return QDate(day.year, day.month, day.day)
