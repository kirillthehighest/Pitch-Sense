"""Algorithm Comparison: metrics, paired differences, breakdowns, agreement and charts."""

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.evaluation.comparison import COMPARED_MODELS, REFERENCE_MODEL, SubsetComparison
from app.services.evaluation import EvaluationResults
from app.ui.context import AppContext
from app.ui.widgets import OUTCOME_NAMES, ChartView, fill_table, make_table, number, percent
from app.visualization import charts

BREAKDOWNS = ("By season", "By actual result", "By matchup type")
VIEWS = ("Tables", "Charts")


class AlgorithmComparisonTab(QWidget):
    """Shows the results of the evaluation log; offers to build the log when it is missing."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self._results: EvaluationResults | None = None

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.backtest_button = QPushButton("Run backtest")
        self.backtest_button.clicked.connect(self._run_backtest)
        self.metrics_table = make_table(
            ["Model", "Accuracy", "Brier score", "Log loss", "Calibration error", "Goals error"],
            stretch_column=0,
        )
        self.differences_table = make_table(
            ["Comparison", "Measure", "Difference", "95% interval", "Better"], stretch_column=0
        )
        self.breakdown_box = QComboBox()
        self.breakdown_box.addItems(list(BREAKDOWNS))
        self.breakdown_box.currentTextChanged.connect(self._show_breakdown)
        self.breakdown_table = make_table(
            ["Subset", "Matches", *COMPARED_MODELS, REFERENCE_MODEL, "Best", "Real lead"],
            stretch_column=0,
        )
        self.agreement_table = make_table(
            ["Models", "Same prediction", "Mean distance"], stretch_column=0
        )
        self.agreement_label = QLabel()
        self.calibration_chart = ChartView("The calibration chart appears after the backtest.")
        self.confusion_box = QComboBox()
        self.confusion_box.currentTextChanged.connect(self._show_confusion)
        self.confusion_chart = ChartView("The confusion matrix appears after the backtest.")

        tables = QWidget()
        tables_layout = QVBoxLayout(tables)
        for title, widget in (
            ("Overall metrics (lower Brier score and log loss are better)", self.metrics_table),
            (
                "Match-by-match differences (real when the interval excludes 0)",
                self.differences_table,
            ),
            ("Where each model does well: Brier score per subset", self.breakdown_box),
            (None, self.breakdown_table),
            ("How different the forecasts are", self.agreement_table),
            (None, self.agreement_label),
        ):
            if title:
                tables_layout.addWidget(QLabel(f"<b>{title}</b>"))
            tables_layout.addWidget(widget)

        confusion = QVBoxLayout()
        model_choice = QFormLayout()
        model_choice.addRow("Confusion matrix of", self.confusion_box)
        confusion.addLayout(model_choice)
        confusion.addWidget(self.confusion_chart)
        charts_page = QWidget()
        charts_layout = QHBoxLayout(charts_page)
        charts_layout.addWidget(self.calibration_chart, stretch=1)
        charts_layout.addLayout(confusion, stretch=1)

        self.views = QTabWidget()
        self.views.addTab(tables, VIEWS[0])
        self.views.addTab(charts_page, VIEWS[1])
        layout = QVBoxLayout(self)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.backtest_button)
        layout.addWidget(self.views)
        self.refresh()

    def refresh(self) -> None:
        evaluation = self._context.evaluation
        if not evaluation.has_log:
            self.summary_label.setText(
                "There is no prediction log yet. Run the backtest (about 8 seconds) to see "
                "the comparison."
            )
            self.backtest_button.show()
            return
        self.backtest_button.hide()
        self._context.run_task(evaluation.results, self._show, self._results_failed)

    def _show(self, results: EvaluationResults) -> None:
        self._results = results
        self.summary_label.setText(
            f"{results.matches} matches, seasons {results.first_season} to "
            f"{results.last_season}, every model predicted in chronological order from the "
            "matches before each day."
        )
        fill_table(
            self.metrics_table,
            [
                [
                    e.model,
                    percent(e.accuracy.value),
                    number(e.brier.value if e.brier else None),
                    number(e.log_loss.value if e.log_loss else None),
                    number(e.calibration_error),
                    number(e.goals_error.value if e.goals_error else None, 3),
                ]
                for e in results.evaluations
            ],
            fit=True,
        )
        fill_table(
            self.differences_table,
            [
                [
                    f"{d.first} v {d.second}",
                    str(d.measure),
                    f"{d.mean:+.4f}",
                    f"[{d.lower:+.4f}, {d.upper:+.4f}]",
                    d.better or "no real difference",
                ]
                for d in results.differences
            ],
        )
        fill_table(
            self.agreement_table,
            [
                [f"{a.first} v {a.second}", percent(a.same_prediction), number(a.mean_distance)]
                for a in results.agreements
            ],
            fit=True,
        )
        self.agreement_label.setText(
            f"All three models predict the same outcome in {percent(results.all_agree)} of matches."
        )
        self._show_breakdown(self.breakdown_box.currentText())
        self.calibration_chart.show_figure(
            charts.calibration_chart(
                {e.model: e.calibration for e in results.evaluations if e.calibration is not None}
            )
        )
        chosen = self.confusion_box.currentText()
        self.confusion_box.clear()
        self.confusion_box.addItems([e.model for e in results.evaluations])
        if chosen:
            self.confusion_box.setCurrentText(chosen)

    def _show_confusion(self, model: str) -> None:
        if self._results is None or not model:
            return
        evaluation = next(e for e in self._results.evaluations if e.model == model)
        self.confusion_chart.show_figure(charts.confusion_chart(model, evaluation.confusion))

    def _show_breakdown(self, name: str) -> None:
        if self._results is None:
            return
        subsets: tuple[SubsetComparison, ...] = {
            BREAKDOWNS[0]: self._results.by_season,
            BREAKDOWNS[1]: self._results.by_outcome,
            BREAKDOWNS[2]: self._results.by_matchup_type,
        }[name]
        fill_table(
            self.breakdown_table,
            [
                [
                    OUTCOME_NAMES.get(s.label, s.label),
                    str(s.matches),
                    *(
                        number(s.brier[model].value)
                        for model in (*COMPARED_MODELS, REFERENCE_MODEL)
                    ),
                    s.best,
                    "yes" if s.lead is not None and s.lead.significant else "no",
                ]
                for s in subsets
            ],
        )

    def _results_failed(self, message: str) -> None:
        # Shown in place rather than in a dialog: every tab change would repeat a dialog.
        self.summary_label.setText(message)
        self.backtest_button.show()

    def _run_backtest(self) -> None:
        self.backtest_button.setEnabled(False)
        self.summary_label.setText("Running the backtest...")
        self._context.run_task(self._context.evaluation.build_log, self._built, self._failed)

    def _built(self, _: object) -> None:
        self.backtest_button.setEnabled(True)
        self.refresh()

    def _failed(self, message: str) -> None:
        self.backtest_button.setEnabled(True)
        self._context.report_error(message)
        self.refresh()
