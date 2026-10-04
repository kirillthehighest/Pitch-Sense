"""Dashboard: what data is loaded and how the models perform overall."""

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from app.services.evaluation import EvaluationResults
from app.ui.context import AppContext
from app.ui.widgets import fill_table, make_table, number, percent

INTRODUCTION = (
    "PitchSense estimates the outcome of football matches with three algorithms implemented "
    "from scratch (Elo rating, Poisson model, logistic regression) and groups teams by "
    "statistical profile with K-Means. Every prediction uses only matches played before it."
)
TABS_GUIDE = (
    "Match Prediction: predict a played match or any fixture of a season.\n"
    "Team Analysis: league table, a team's record, form and profile group.\n"
    "Algorithm Comparison: which model is better, where, and how much they differ."
)


class DashboardTab(QWidget):
    """Shows the data summary and, when the prediction log exists, the headline results."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        summary = context.catalog.summary()
        layout = QVBoxLayout(self)

        title = QLabel("<h2>PitchSense</h2>")
        introduction = QLabel(INTRODUCTION)
        introduction.setWordWrap(True)
        self.data_label = QLabel(
            f"<b>Data:</b> {summary.competition_name}, {summary.seasons} seasons "
            f"({summary.first_season} to {summary.last_season}), {summary.matches} matches, "
            f"{summary.teams} teams."
        )
        self.results_label = QLabel()
        self.results_label.setWordWrap(True)
        self.results_table = make_table(
            ["Model", "Accuracy", "Brier score", "Log loss"], stretch_column=0
        )
        self.backtest_button = QPushButton("Run backtest")
        self.backtest_button.clicked.connect(self._run_backtest)
        guide = QLabel(TABS_GUIDE)

        for widget in (
            title,
            introduction,
            self.data_label,
            self.results_label,
            self.results_table,
            self.backtest_button,
            guide,
        ):
            layout.addWidget(widget)
        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        """Show the headline results, or offer to run the backtest when there is no log."""
        evaluation = self._context.evaluation
        if not evaluation.has_log:
            self.results_label.setText(
                "No evaluation yet. Run the backtest (about 8 seconds) to compare the models."
            )
            self.results_table.hide()
            self.backtest_button.show()
            return
        self.backtest_button.hide()
        self._context.run_task(evaluation.results, self._show_results, self._context.report_error)

    def _show_results(self, results: EvaluationResults) -> None:
        self.results_label.setText(
            f"<b>Evaluation:</b> {results.matches} matches, seasons {results.first_season} to "
            f"{results.last_season}, predicted in chronological order. "
            "Lower Brier score and log loss are better."
        )
        fill_table(
            self.results_table,
            [
                [
                    evaluation.model,
                    percent(evaluation.accuracy.value),
                    number(evaluation.brier.value if evaluation.brier else None),
                    number(evaluation.log_loss.value if evaluation.log_loss else None),
                ]
                for evaluation in results.evaluations
            ],
            fit=True,
        )
        self.results_table.show()

    def _run_backtest(self) -> None:
        self.backtest_button.setEnabled(False)
        self.results_label.setText("Running the backtest...")
        self._context.run_task(
            self._context.evaluation.build_log, self._backtest_done, self._backtest_failed
        )

    def _backtest_done(self, _: object) -> None:
        self.backtest_button.setEnabled(True)
        self.refresh()

    def _backtest_failed(self, message: str) -> None:
        self.backtest_button.setEnabled(True)
        self._context.report_error(message)
        self.refresh()
