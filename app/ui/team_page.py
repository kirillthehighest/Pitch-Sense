"""Echipe: one club's page (Phase 19), in the manner of a club page of a sports channel: the crest
and the name in large letters, the season in numbers, the form, the next match with its
prediction, the last results, the club's K-Means profile in plain words and its charts."""

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.prediction.outputs import ModelName
from app.services.formatting import season_text
from app.services.predictions import MatchForecast
from app.services.teams import RatingSeason, SeasonGroups, TeamOverview
from app.statistics.team_statistics import TeamStatistics
from app.ui.brand import team_badge
from app.ui.context import AppContext, LeagueServices
from app.ui.match_widgets import MatchRow
from app.ui.widgets import (
    ChartView,
    FormStrip,
    PageTabs,
    ReflowGrid,
    ResponsiveBox,
    StatTile,
    card,
    label,
    paint_league_card,
)
from app.visualization.charts import elo_history_chart, team_groups_chart

CREST_SIZE = 120
CHART_HEIGHT = 540  # room for the names of twenty teams on the groups chart
TILE_WIDTH = 128
MIDDLE_BREAKPOINT = 1000  # narrower, the form, matches and profile cards stack
LAST_RESULTS = 5
TILES = ("Loc", "Meciuri", "Victorii", "Goluri marcate", "Goluri primite", "Puncte")
GROUPS_EXPLANATION = (
    "K‑Means grupează echipele după șase valori pe meci ale unui sezon: goluri marcate și primite, "
    "șuturi pe poartă date și primite, puncte și diferența dintre punctele de acasă și din "
    "deplasare. Rezultă patru profiluri: Elită, Jumătatea de sus, Jumătatea de jos (puternică "
    "acasă) și Slabă peste tot. Grupul de dinaintea sezonului vine din sezonul anterior; grupul "
    "sezonului descrie sezonul încheiat."
)
GROUPS_IN_PROGRESS = (
    "Sezonul este în desfășurare. Grupurile K‑Means descriu sezoane încheiate, așa că apar după "
    "ultimul meci al sezonului."
)
GROUPS_NO_STATISTICS = "Sezonul nu are statistici de șuturi, deci echipele nu pot fi grupate."
SEASON_NOT_FINISHED = "Sezonul nu este încheiat"
NOT_READY = "Predicțiile ligii se pregătesc; meciurile apar imediat ce sunt gata."


@dataclass(frozen=True, eq=False)
class TeamAnswer:
    """Everything the page shows for one team and season."""

    overview: TeamOverview
    teams: int
    elo_history: tuple[RatingSeason, ...]
    groups: SeasonGroups | None
    groups_problem: str | None
    matches: list[MatchForecast] | None  # None while the league's predictions are prepared


def record_text(record: TeamStatistics) -> str:
    return (
        f"{record.played} meciuri: {record.wins} V, {record.draws} E, {record.losses} Î; "
        f"goluri {record.goals_for}–{record.goals_against}; {record.points} puncte"
    )


class TeamHeader(QFrame):
    """The crest and the name in large capitals on a band in the league's colours."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(170)
        self.crest = QLabel()
        self.name = label(role="title", wrap=True)
        self.caption = label(role="subtitle", wrap=True)
        self.eyebrow = label(role="eyebrow")
        names = QVBoxLayout()
        names.setSpacing(2)
        names.addStretch()
        names.addWidget(self.eyebrow)
        names.addWidget(self.name)
        names.addWidget(self.caption)
        names.addStretch()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 18, 28, 18)
        layout.setSpacing(24)
        layout.addWidget(self.crest)
        layout.addLayout(names, stretch=1)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        paint_league_card(painter, QRectF(self.rect()))
        painter.end()


class TeamPage(QWidget):
    """Choose a season and a team; everything else follows."""

    title = "Echipe"
    subtitle = "Pagina unei echipe: sezonul în cifre, forma, meciurile, profilul și ratingul Elo."

    def __init__(self, context: AppContext, open_match: Callable[[MatchForecast], None]) -> None:
        super().__init__()
        self._context = context
        self._open_match = open_match
        self._league: LeagueServices | None = None
        self.answer: TeamAnswer | None = None
        self.season_box = QComboBox()
        self.season_box.currentIndexChanged.connect(self._season_changed)
        self.team_box = QComboBox()
        self.team_box.setMinimumWidth(220)
        self.team_box.currentIndexChanged.connect(self.refresh)
        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.addWidget(label("Sezon", "caption"))
        controls.addWidget(self.season_box)
        controls.addSpacing(12)
        controls.addWidget(label("Echipă", "caption"))
        controls.addWidget(self.team_box)
        controls.addStretch()

        self.header = TeamHeader()
        self.tiles = {name: StatTile(name) for name in TILES}
        tiles = ReflowGrid(TILE_WIDTH, spacing=12)
        for tile in self.tiles.values():
            tiles.add(tile)

        form_card, form_layout = card("Forma")
        self.form_strip = FormStrip()
        form_layout.addWidget(self.form_strip)
        self.home_label = label(wrap=True)
        self.away_label = label(wrap=True)
        self.shots_label = label(wrap=True)
        for name, widget in (
            ("Acasă", self.home_label),
            ("În deplasare", self.away_label),
            ("Șuturi pe poartă pe meci", self.shots_label),
        ):
            form_layout.addWidget(label(name.upper(), "overline"))
            form_layout.addWidget(widget)
        form_layout.addStretch()

        matches_card, matches_layout = card("Meciurile echipei")
        self.next_title = label("URMĂTORUL MECI", "overline")
        self.matches_note = label(role="caption", wrap=True)
        self.next_layout = QVBoxLayout()
        self.next_layout.setSpacing(0)
        self.last_layout = QVBoxLayout()
        self.last_layout.setSpacing(0)
        matches_layout.addWidget(self.next_title)
        matches_layout.addLayout(self.next_layout)
        matches_layout.addWidget(label("ULTIMELE REZULTATE", "overline"))
        matches_layout.addLayout(self.last_layout)
        matches_layout.addWidget(self.matches_note)
        matches_layout.addStretch()
        self.match_rows: list[MatchRow] = []

        profile_card, profile_layout = card("Profilul K‑Means")
        self.pre_season_label = label(role="strong", wrap=True)
        self.season_group_label = label(role="strong", wrap=True)
        profile_layout.addWidget(label("ÎNAINTEA SEZONULUI", "overline"))
        profile_layout.addWidget(self.pre_season_label)
        profile_layout.addWidget(label("SEZONUL", "overline"))
        profile_layout.addWidget(self.season_group_label)
        profile_layout.addWidget(label(GROUPS_EXPLANATION, "caption", wrap=True))
        profile_layout.addStretch()

        self.elo_chart = ChartView("Ratingul Elo al echipei apare aici.")
        self.groups_chart = ChartView("Grupurile echipelor din sezon apar aici.")
        for chart in (self.elo_chart, self.groups_chart):
            chart.setMinimumHeight(CHART_HEIGHT)
        charts_card, charts_layout = card()
        self.views = PageTabs()
        self.views.addTab(self.elo_chart, "Rating Elo")
        self.views.addTab(self.groups_chart, "Grupuri")
        charts_layout.addWidget(self.views)

        # Side by side in a wide window, one under the other in a narrow one.
        middle = ResponsiveBox(MIDDLE_BREAKPOINT, spacing=16)
        middle.add(form_card, stretch=2)
        middle.add(matches_card, stretch=3)
        middle.add(profile_card, stretch=2)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addLayout(controls)
        layout.addWidget(self.header)
        layout.addWidget(tiles)
        layout.addWidget(middle)
        layout.addWidget(charts_card)
        layout.addStretch()

    def show_league(self, league: LeagueServices) -> None:
        """Start from the latest season and "your team" (else the leader)."""
        self._league = league
        self.team_box.blockSignals(True)
        self.team_box.clear()
        self.team_box.blockSignals(False)
        self.season_box.blockSignals(True)
        self.season_box.clear()
        for season in reversed(league.catalog.seasons()):
            self.season_box.addItem(season_text(season), season)
        self.season_box.blockSignals(False)
        self._season_changed()

    def show_team(self, team: str, season: str | None = None) -> None:
        """Open a team's page, in ``season`` or else the latest season it played."""
        catalog = self._league.catalog
        if season is None:
            season = next(s for s in reversed(catalog.seasons()) if team in catalog.teams(s))
        self.season_box.setCurrentIndex(self.season_box.findData(season))
        self.team_box.setCurrentText(team)

    def refresh(self) -> None:
        """Gather the page of the chosen team in the background."""
        season, team = self.season_box.currentData(), self.team_box.currentText()
        if self._league is None or season is None or not team:
            return
        league = self._league

        def answer() -> TeamAnswer:
            teams = league.teams
            groups, problem = None, None
            if season == teams.in_progress:
                problem = GROUPS_IN_PROGRESS
            else:
                try:
                    groups = teams.season_groups(season)
                except ValueError:  # a season without shot statistics has no groups
                    problem = GROUPS_NO_STATISTICS
            predictions = league.predictions
            return TeamAnswer(
                overview=teams.overview(season, team),
                teams=len(teams.standings(season)),
                elo_history=teams.elo_history(team),
                groups=groups,
                groups_problem=problem,
                matches=(
                    predictions.team_matches(team, season) if predictions.is_prepared else None
                ),
            )

        self._context.run_task(answer, self._show, self._context.report_error)

    def _show(self, answer: TeamAnswer) -> None:
        self.answer = answer
        overview = answer.overview
        favourite = self._context.preferences.favourite
        is_favourite = favourite is not None and favourite.team == overview.team
        self.header.crest.setPixmap(team_badge(overview.team, CREST_SIZE, highlighted=is_favourite))
        self.header.name.setText(overview.team.upper())
        self.header.eyebrow.setText(
            (("Echipa ta · " if is_favourite else "") + self._league.name).upper()
        )
        state = "sezon în desfășurare" if overview.in_progress else "sezon încheiat"
        self.header.caption.setText(
            f"{season_text(overview.season)} · locul {overview.position} din {answer.teams} · "
            f"{state}"
        )
        record = overview.record
        for name, value in zip(
            TILES,
            (
                overview.position,
                record.played,
                record.wins,
                record.goals_for,
                record.goals_against,
                record.points,
            ),
            strict=True,
        ):
            self.tiles[name].set_value(str(value))
        self.form_strip.set_results([result.value for result in overview.form])
        self.home_label.setText(record_text(overview.home))
        self.away_label.setText(record_text(overview.away))
        shots = overview.match_statistics
        self.shots_label.setText(
            f"{shots.shots_on_target:.2f} ale echipei, {shots.opponent_shots_on_target:.2f} ale "
            "adversarilor".replace(".", ",")
        )
        self.pre_season_label.setText(overview.pre_season_group)
        self.season_group_label.setText(overview.season_group or SEASON_NOT_FINISHED)
        self._show_matches(answer.matches, overview.team if is_favourite else None)
        self.elo_chart.show_figure(
            elo_history_chart(overview.team, answer.elo_history, season=overview.season)
        )
        if answer.groups is not None:
            self.groups_chart.show_figure(team_groups_chart(answer.groups, team=overview.team))
        else:
            self.groups_chart.show_message(answer.groups_problem or GROUPS_NO_STATISTICS)

    def _show_matches(self, matches: list[MatchForecast] | None, favourite: str | None) -> None:
        for row in self.match_rows:
            row.setParent(None)
            row.deleteLater()
        self.match_rows = []
        if matches is None:
            self.next_title.hide()
            self.matches_note.setText(NOT_READY)
            return
        upcoming = [m for m in matches if m.played is None]
        played = [m for m in matches if m.played is not None][-LAST_RESULTS:][::-1]
        self.next_title.setVisible(bool(upcoming))
        for forecast, layout in [(m, self.next_layout) for m in upcoming[:1]] + [
            (m, self.last_layout) for m in played
        ]:
            row = MatchRow(
                forecast, ModelName.LOGISTIC_REGRESSION, favourite, show_date=True, stacked=True
            )
            row.clicked.connect(lambda _, f=forecast: self._open_match(f))
            layout.addWidget(row)
            self.match_rows.append(row)
        self.matches_note.setText(
            "Probabilitățile sunt ale regresiei logistice; apasă pe un meci pentru toate modelele."
        )

    def _season_changed(self) -> None:
        season = self.season_box.currentData()
        if season is None or self._league is None:
            return
        teams = self._league.catalog.teams(season)
        current = self.team_box.currentText()
        favourite = self._context.preferences.favourite
        self.team_box.blockSignals(True)
        self.team_box.clear()
        self.team_box.addItems(teams)
        if current in teams:
            self.team_box.setCurrentText(current)
        elif favourite and favourite.competition == self._league.code and favourite.team in teams:
            self.team_box.setCurrentText(favourite.team)
        else:
            leader = self._league.teams.standings(season)[0].team
            self.team_box.setCurrentText(leader)
        self.team_box.blockSignals(False)
        self.refresh()
