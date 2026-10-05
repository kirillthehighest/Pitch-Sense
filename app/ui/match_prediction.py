"""Predicție: every model's forecast for a played match or any fixture of a season, shown as a
match card with one probability bar per model."""

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.data.models import Match
from app.data.preprocessing import season_date_window
from app.prediction.prediction_engine import FixturePrediction
from app.services.formatting import date_text, number, percent, season_text
from app.services.labels import model_label, outcome_label
from app.services.predictions import summarize
from app.ui.brand import team_badge
from app.ui.context import AppContext, LeagueServices
from app.ui.widgets import (
    BarRow,
    ChartView,
    ProbabilityBars,
    card,
    fill_table,
    label,
    make_table,
)
from app.visualization.charts import score_heatmap
from app.visualization.palette import LINE

NO_SCORES = "Probabilitățile scorurilor (modelul Poisson) apar aici după predicție."
NO_MATCH = "Alege un meci și apasă „Calculează predicția”."
SAME_TEAM = "Alege două echipe diferite."
BADGE_SIZE = 76
CHOICE_WIDTH = 400


def match_label(match: Match) -> str:
    return (
        f"{date_text(match.match_date)}   {match.home_team} {match.home_goals}–"
        f"{match.away_goals} {match.away_team}"
    )


class MatchPredictionTab(QWidget):
    """Choose a fixture, predict it and show each model's probabilities."""

    title = "Predicție"
    subtitle = (
        "Probabilitățile fiecărui model pentru un meci, calculate doar din meciurile anterioare."
    )

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self._league: LeagueServices | None = None

        self.season_box = QComboBox()
        self.season_box.currentIndexChanged.connect(self._season_changed)
        self.played_button = QRadioButton("Meci jucat")
        self.fixture_button = QRadioButton("Orice meci")
        self.played_button.setChecked(True)
        mode = QButtonGroup(self)
        mode.addButton(self.played_button)
        mode.addButton(self.fixture_button)
        self.played_button.toggled.connect(self._mode_changed)
        self.match_box = QComboBox()
        self.home_box = QComboBox()
        self.away_box = QComboBox()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.predict_button = QPushButton("Calculează predicția")
        self.predict_button.setProperty("role", "primary")
        self.predict_button.clicked.connect(self.predict)
        self.status_label = label(role="caption")

        choice_card, choice_layout = card("Meciul")
        choice = QFormLayout()
        choice.setSpacing(12)
        self._choice = choice
        choice.addRow("Sezon", self.season_box)
        modes = QHBoxLayout()
        modes.setSpacing(16)
        modes.addWidget(self.played_button)
        modes.addWidget(self.fixture_button)
        modes.addStretch()
        choice.addRow("Tip", modes)
        choice.addRow("Meci", self.match_box)
        choice.addRow("Gazde", self.home_box)
        choice.addRow("Oaspeți", self.away_box)
        choice.addRow("Data", self.date_edit)
        choice_layout.addLayout(choice)
        choice_layout.addWidget(self.predict_button)
        choice_layout.addWidget(self.status_label)

        details_card, details_layout = card("Probabilitățile, în cifre")
        self.probability_table = make_table(
            ["Model", "Gazde", "Egal", "Oaspeți", "Cel mai probabil"], stretch_column=0
        )
        details_layout.addWidget(self.probability_table)

        poisson_card, poisson_layout = card("Poisson: goluri și scoruri")
        self.goals_label = label(wrap=True)
        self.scores_table = make_table(["Scor", "Probabilitate"], stretch_column=0)
        poisson_layout.addWidget(self.goals_label)
        poisson_layout.addWidget(self.scores_table)

        chart_card, chart_layout = card()
        self.score_chart = ChartView(NO_SCORES)
        self.score_chart.setMinimumHeight(460)
        chart_layout.addWidget(self.score_chart)

        left = QVBoxLayout()
        left.setSpacing(16)
        for widget in (choice_card, poisson_card):
            widget.setFixedWidth(CHOICE_WIDTH)
            widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
            left.addWidget(widget)
        left.addStretch()
        right = QVBoxLayout()
        right.setSpacing(16)
        right.addWidget(self._match_card())
        right.addWidget(details_card)
        right.addWidget(chart_card)
        right.addStretch()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addLayout(left)
        layout.addLayout(right, stretch=1)
        self._mode_changed()

    def _match_card(self) -> QFrame:
        match_card, match_layout = card()
        match_layout.setSpacing(14)
        self.fixture_label = label(role="eyebrow")
        self.fixture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.home_badge, self.away_badge = QLabel(), QLabel()
        self.home_name = label(role="team", wrap=True)
        self.away_name = label(role="team", wrap=True)
        self.score_label = label("VS", "score")
        self.result_label = label(role="caption", wrap=True)
        for widget in (self.home_badge, self.away_badge, self.home_name, self.away_name):
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        teams = QGridLayout()
        teams.setHorizontalSpacing(12)
        teams.setVerticalSpacing(6)
        teams.addWidget(self.home_badge, 0, 0)
        teams.addWidget(self.score_label, 0, 1, 2, 1)
        teams.addWidget(self.away_badge, 0, 2)
        teams.addWidget(self.home_name, 1, 0)
        teams.addWidget(self.away_name, 1, 2)
        teams.setColumnStretch(0, 1)
        teams.setColumnStretch(2, 1)
        teams.setColumnMinimumWidth(1, 180)
        self.bars = ProbabilityBars()
        match_layout.addWidget(self.fixture_label)
        match_layout.addLayout(teams)
        match_layout.addWidget(self.result_label)
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {LINE};")
        match_layout.addWidget(divider)
        match_layout.addWidget(label("PROBABILITĂȚILE MODELELOR", "overline"))
        match_layout.addWidget(self.bars)
        return match_card

    def show_league(self, league: LeagueServices) -> None:
        """Offer the league's seasons, latest first, and start from "your team" when it plays."""
        self._league = league
        self.season_box.blockSignals(True)
        self.season_box.clear()
        for season in reversed(league.catalog.seasons()):
            self.season_box.addItem(season_text(season), season)
        self.season_box.blockSignals(False)
        self._season_changed()
        self._clear()

    def predict(self) -> None:
        """Predict the chosen fixture in the background."""
        season = self.season_box.currentData()
        if self.played_button.isChecked():
            match: Match = self.match_box.currentData()
            home, away, day = match.home_team, match.away_team, match.match_date
        else:
            home, away = self.home_box.currentText(), self.away_box.currentText()
            day = self.date_edit.date().toPython()
            if home == away:
                self.status_label.setText(SAME_TEAM)
                return
        self.predict_button.setEnabled(False)
        self.status_label.setText("Se calculează predicțiile…")
        predictions = self._league.predictions
        self._context.run_task(
            lambda: predictions.predict(season, home, away, day), self._show, self._failed
        )

    def _clear(self) -> None:
        self.fixture_label.setText(self._league.name.upper() if self._league else "")
        for badge in (self.home_badge, self.away_badge):
            badge.clear()
        self.home_name.clear()
        self.away_name.clear()
        self.score_label.setText("VS")
        self.result_label.setText(NO_MATCH)
        self.bars.set_rows(())
        fill_table(self.probability_table, [])
        self.goals_label.clear()
        fill_table(self.scores_table, [])
        self.score_chart.show_message(NO_SCORES)

    def _show(self, fixture: FixturePrediction) -> None:
        self.predict_button.setEnabled(True)
        self.status_label.setText("")
        self.fixture_label.setText(
            f"{self._league.name} · {season_text(fixture.season)} · "
            f"{date_text(fixture.match_date)}".upper()
        )
        favourite = self._favourite_in([fixture.home_team, fixture.away_team])
        for badge, name, team in (
            (self.home_badge, self.home_name, fixture.home_team),
            (self.away_badge, self.away_name, fixture.away_team),
        ):
            badge.setPixmap(team_badge(team, BADGE_SIZE, highlighted=team == favourite))
            name.setText(team.upper())
        if fixture.played is None:
            self.score_label.setText("VS")
            result = "Meci nejucat: o predicție ipotetică."
        else:
            played = fixture.played
            self.score_label.setText(f"{played.home_goals} – {played.away_goals}")
            result = (
                f"Rezultat real: {played.home_goals}–{played.away_goals} "
                f"({outcome_label(played.result.value)})."
            )
        if not fixture.predictions:
            result += " Niciun model nu are destule meciuri anterioare pentru această dată."
        self.result_label.setText(result)
        summaries = [summarize(prediction) for prediction in fixture.predictions.values()]
        self.bars.set_rows(
            [BarRow(model_label(str(s.model)), s.home_win, s.draw, s.away_win) for s in summaries]
        )
        fill_table(
            self.probability_table,
            [
                [
                    model_label(str(s.model)),
                    percent(s.home_win),
                    percent(s.draw),
                    percent(s.away_win),
                    outcome_label(s.most_likely.value),
                ]
                for s in summaries
            ],
            fit=True,
        )
        poisson = next((s for s in summaries if s.expected_goals is not None), None)
        if poisson is None or poisson.score_probabilities is None:
            self.goals_label.setText("Nu există o predicție Poisson pentru acest meci.")
            fill_table(self.scores_table, [])
            self.score_chart.show_message("Nu există o predicție Poisson pentru acest meci.")
            return
        home_goals, away_goals = poisson.expected_goals
        self.goals_label.setText(
            f"Goluri așteptate: {fixture.home_team} {number(home_goals, 2)}, "
            f"{fixture.away_team} {number(away_goals, 2)}"
        )
        fill_table(
            self.scores_table,
            [
                [f"{home}–{away}", percent(probability)]
                for home, away, probability in poisson.top_scores
            ],
            fit=True,
        )
        self.score_chart.show_figure(
            score_heatmap(fixture.home_team, fixture.away_team, poisson.score_probabilities)
        )

    def _failed(self, message: str) -> None:
        self.predict_button.setEnabled(True)
        self.status_label.setText("")
        self._context.report_error(message)

    def _season_changed(self) -> None:
        season = self.season_box.currentData()
        if season is None or self._league is None:
            return
        catalog = self._league.catalog
        matches = catalog.season_matches(season)
        self.match_box.clear()
        for match in matches:
            self.match_box.addItem(match_label(match), match)
        teams = catalog.teams(season)
        for box in (self.home_box, self.away_box):
            box.clear()
            box.addItems(teams)
        self.away_box.setCurrentIndex(1 if len(teams) > 1 else 0)
        favourite = self._favourite_in(teams)
        if favourite is not None:
            last = max(
                (i for i, m in enumerate(matches) if favourite in (m.home_team, m.away_team)),
                default=None,
            )
            if last is not None:
                self.match_box.setCurrentIndex(last)
            self.home_box.setCurrentText(favourite)
        first_day, last_day = season_date_window(season)
        self.date_edit.setDateRange(_qdate(first_day), _qdate(last_day))
        self.date_edit.setDate(_qdate(matches[len(matches) // 2].match_date))

    def _favourite_in(self, teams: list[str]) -> str | None:
        favourite = self._context.preferences.favourite
        if favourite and favourite.competition == self._league.code and favourite.team in teams:
            return favourite.team
        return None

    def _mode_changed(self) -> None:
        """Show only the fields of the chosen mode."""
        played = self.played_button.isChecked()
        self._choice.setRowVisible(self.match_box, played)
        for widget in (self.home_box, self.away_box, self.date_edit):
            self._choice.setRowVisible(widget, not played)


def _qdate(day) -> QDate:
    return QDate(day.year, day.month, day.day)
