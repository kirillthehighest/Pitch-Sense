"""Match Prediction: every model's forecast for a played match or any fixture of a season."""

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app.data.models import Match
from app.data.preprocessing import season_date_window
from app.prediction.prediction_engine import FixturePrediction
from app.services.predictions import summarize
from app.ui.context import AppContext
from app.ui.widgets import OUTCOME_NAMES, ChartView, fill_table, make_table, number, percent
from app.visualization.charts import score_heatmap

NO_SCORES = "The Poisson score probabilities appear here after a prediction."


def match_label(match: Match) -> str:
    return (
        f"{match.match_date.isoformat()}   {match.home_team} {match.home_goals}-"
        f"{match.away_goals} {match.away_team}"
    )


class MatchPredictionTab(QWidget):
    """Choose a fixture, predict it and show each model's probabilities."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context

        self.season_box = QComboBox()
        self.season_box.addItems(list(reversed(context.catalog.seasons())))
        self.season_box.currentTextChanged.connect(self._season_changed)

        self.played_button = QRadioButton("Played match")
        self.fixture_button = QRadioButton("Any fixture")
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
        self.date_edit.setDisplayFormat("yyyy-MM-dd")

        self.predict_button = QPushButton("Predict")
        self.predict_button.clicked.connect(self.predict)
        self.status_label = QLabel()

        choice = QFormLayout()
        self._choice = choice
        choice.addRow("Season", self.season_box)
        modes = QHBoxLayout()
        modes.addWidget(self.played_button)
        modes.addWidget(self.fixture_button)
        choice.addRow("Fixture", modes)
        choice.addRow("Match", self.match_box)
        choice.addRow("Home team", self.home_box)
        choice.addRow("Away team", self.away_box)
        choice.addRow("Date", self.date_edit)

        self.fixture_label = QLabel()
        self.result_label = QLabel()
        self.probability_table = make_table(
            ["Model", "Home win", "Draw", "Away win", "Most likely"], stretch_column=0
        )
        self.goals_label = QLabel()
        self.scores_table = make_table(["Score", "Probability"])
        poisson_box = QGroupBox("Poisson: expected goals and most likely scores")
        poisson_layout = QVBoxLayout(poisson_box)
        poisson_layout.addWidget(self.goals_label)
        poisson_layout.addWidget(self.scores_table)

        self.score_chart = ChartView(NO_SCORES)

        left = QVBoxLayout()
        left.addLayout(choice)
        left.addWidget(self.predict_button)
        left.addWidget(self.status_label)
        left.addWidget(self.fixture_label)
        left.addWidget(self.result_label)
        left.addWidget(self.probability_table)
        left.addWidget(poisson_box)
        left.addStretch()
        layout = QHBoxLayout(self)
        layout.addLayout(left, stretch=1)
        layout.addWidget(self.score_chart, stretch=1)

        self._season_changed(self.season_box.currentText())
        self._mode_changed()

    def predict(self) -> None:
        """Predict the chosen fixture in the background."""
        season = self.season_box.currentText()
        if self.played_button.isChecked():
            match: Match = self.match_box.currentData()
            home, away, day = match.home_team, match.away_team, match.match_date
        else:
            home, away = self.home_box.currentText(), self.away_box.currentText()
            day = self.date_edit.date().toPython()
        self.predict_button.setEnabled(False)
        self.status_label.setText("Computing the predictions...")
        self._context.run_task(
            lambda: self._context.predictions.predict(season, home, away, day),
            self._show,
            self._failed,
        )

    def _show(self, fixture: FixturePrediction) -> None:
        self.predict_button.setEnabled(True)
        self.status_label.setText("")
        self.fixture_label.setText(
            f"<b>{fixture.home_team} v {fixture.away_team}</b>, {fixture.match_date.isoformat()}"
            f" ({fixture.season}), predicted from the matches before this date"
        )
        if fixture.played is None:
            self.result_label.setText("Not played: a hypothetical fixture.")
        else:
            played = fixture.played
            self.result_label.setText(
                f"Actual result: {played.home_goals}-{played.away_goals} "
                f"({OUTCOME_NAMES[played.result.value]})"
            )
        if not fixture.predictions:
            self.result_label.setText(
                self.result_label.text() + " No model has enough earlier data for this date."
            )
        summaries = [summarize(prediction) for prediction in fixture.predictions.values()]
        fill_table(
            self.probability_table,
            [
                [
                    str(s.model),
                    percent(s.home_win),
                    percent(s.draw),
                    percent(s.away_win),
                    OUTCOME_NAMES[s.most_likely.value],
                ]
                for s in summaries
            ],
            fit=True,
        )
        poisson = next((s for s in summaries if s.expected_goals is not None), None)
        if poisson is None or poisson.score_probabilities is None:
            self.goals_label.setText("No Poisson prediction for this fixture.")
            fill_table(self.scores_table, [])
            self.score_chart.show_message("No Poisson prediction for this fixture.")
            return
        home_goals, away_goals = poisson.expected_goals
        self.goals_label.setText(
            f"Expected goals: {fixture.home_team} {number(home_goals, 2)}, "
            f"{fixture.away_team} {number(away_goals, 2)}"
        )
        fill_table(
            self.scores_table,
            [
                [f"{home}-{away}", percent(probability)]
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

    def _season_changed(self, season: str) -> None:
        if not season:
            return
        matches = self._context.catalog.season_matches(season)
        self.match_box.clear()
        for match in matches:
            self.match_box.addItem(match_label(match), match)
        teams = self._context.catalog.teams(season)
        for box in (self.home_box, self.away_box):
            box.clear()
            box.addItems(teams)
        self.away_box.setCurrentIndex(1 if len(teams) > 1 else 0)
        first_day, last_day = season_date_window(season)
        self.date_edit.setDateRange(_qdate(first_day), _qdate(last_day))
        self.date_edit.setDate(_qdate(matches[len(matches) // 2].match_date))

    def _mode_changed(self) -> None:
        """Show only the fields of the chosen mode."""
        played = self.played_button.isChecked()
        self._choice.setRowVisible(self.match_box, played)
        for widget in (self.home_box, self.away_box, self.date_edit):
            self._choice.setRowVisible(widget, not played)


def _qdate(day) -> QDate:
    return QDate(day.year, day.month, day.day)
