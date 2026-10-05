"""Modele: the comparison of the algorithms in one league, as tables and charts."""

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.evaluation.comparison import (
    COMPARED_MODELS,
    MATCHUP_TYPES,
    REFERENCE_MODEL,
    SubsetComparison,
)
from app.services.evaluation import EvaluationResults
from app.services.formatting import number, percent, quantity, season_text, signed
from app.services.labels import MEASURE_LABELS, OUTCOME_LABELS, model_label
from app.ui.context import AppContext, LeagueServices
from app.ui.widgets import (
    ChartView,
    PageTabs,
    card,
    fill_table,
    label,
    make_table,
    unreadable_log_text,
)
from app.visualization import charts

BREAKDOWNS = ("Pe sezoane", "Pe rezultatul real", "Pe tipuri de meciuri")
VIEWS = ("Tabele", "Grafice")
MATCHUP_LABELS = dict(
    zip(
        MATCHUP_TYPES,
        (
            "cu o echipă promovată",
            "cu o echipă de elită",
            "echipe din același grup",
            "echipe din grupuri diferite",
        ),
        strict=True,
    )
)


def subset_label(label_text: str) -> str:
    """The Romanian name of a subset: a season, an actual result or a type of match."""
    if label_text in OUTCOME_LABELS:
        return OUTCOME_LABELS[label_text]
    return MATCHUP_LABELS.get(label_text, season_text(label_text))


class AlgorithmComparisonTab(QWidget):
    """Shows the results of a league's prediction log; offers to build the log when missing."""

    title = "Modele"
    subtitle = "Cât de bine prezice fiecare algoritm, unde și cât de diferit, meci cu meci."

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self._league: LeagueServices | None = None
        self._results: EvaluationResults | None = None

        self.summary_label = label(role="caption", wrap=True)
        self.backtest_button = QPushButton("Rulează backtestul")
        self.backtest_button.setProperty("role", "primary")
        self.backtest_button.clicked.connect(self._run_backtest)
        self.metrics_table = make_table(
            [
                "Model",
                "Acuratețe",
                "Scor Brier",
                "Pierdere logaritmică",
                "Eroare de calibrare",
                "Eroarea golurilor",
            ],
            stretch_column=0,
        )
        self.differences_table = make_table(
            ["Comparație", "Măsură", "Diferență", "Interval de 95%", "Mai bun"], stretch_column=0
        )
        self.breakdown_box = QComboBox()
        self.breakdown_box.addItems(list(BREAKDOWNS))
        self.breakdown_box.currentTextChanged.connect(self._show_breakdown)
        self.breakdown_table = make_table(
            [
                "Categorie",
                "Meciuri",
                *(model_label(m) for m in (*COMPARED_MODELS, REFERENCE_MODEL)),
                "Cel mai bun",
                "Avantaj real",
            ],
            stretch_column=0,
        )
        self.agreement_table = make_table(
            ["Modele", "Același rezultat prezis", "Distanța medie"], stretch_column=0
        )
        self.agreement_label = label(role="caption", wrap=True)
        self.calibration_chart = ChartView("Graficul calibrării apare după backtest.")
        self.confusion_box = QComboBox()
        self.confusion_box.currentIndexChanged.connect(self._show_confusion)
        self.confusion_chart = ChartView("Matricea de confuzie apare după backtest.")

        tables = QWidget()
        tables_layout = QVBoxLayout(tables)
        tables_layout.setContentsMargins(0, 8, 0, 0)
        tables_layout.setSpacing(12)
        for title, widget in (
            ("Măsurile generale (scorul Brier și pierderea logaritmică: mai mic e mai bine)",
             self.metrics_table),
            ("Diferențele meci cu meci (reale când intervalul nu conține 0)",
             self.differences_table),
            ("Unde se descurcă fiecare model: scorul Brier pe subseturi", self.breakdown_box),
            (None, self.breakdown_table),
            ("Cât de diferite sunt predicțiile", self.agreement_table),
            (None, self.agreement_label),
        ):  # fmt: skip
            if title:
                tables_layout.addWidget(label(title, "section"))
            tables_layout.addWidget(widget)

        confusion = QVBoxLayout()
        model_choice = QFormLayout()
        model_choice.addRow(label("Matricea de confuzie pentru", "caption"), self.confusion_box)
        confusion.addLayout(model_choice)
        confusion.addWidget(self.confusion_chart, stretch=1)
        charts = QHBoxLayout()
        charts.setSpacing(16)
        charts.addWidget(self.calibration_chart, stretch=1)
        charts.addLayout(confusion, stretch=1)
        charts_page = QWidget()
        charts_layout = QVBoxLayout(charts_page)
        charts_layout.setContentsMargins(0, 8, 0, 0)
        charts_layout.addLayout(charts)
        charts_layout.addStretch()

        content, content_layout = card()
        content_layout.addWidget(self.summary_label)
        content_layout.addWidget(self.backtest_button)
        self.views = PageTabs()
        self.views.addTab(tables, VIEWS[0])
        self.views.addTab(charts_page, VIEWS[1])
        content_layout.addWidget(self.views)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content)
        layout.addStretch()  # the card ends with its content

    def show_league(self, league: LeagueServices) -> None:
        self._league = league
        self._results = None
        for table in (
            self.metrics_table,
            self.differences_table,
            self.breakdown_table,
            self.agreement_table,
        ):
            fill_table(table, [])
        self.agreement_label.clear()
        self.calibration_chart.show_message("Graficul calibrării apare după backtest.")
        self.confusion_chart.show_message("Matricea de confuzie apare după backtest.")
        self.confusion_box.blockSignals(True)
        self.confusion_box.clear()
        self.confusion_box.blockSignals(False)
        self.refresh()

    def refresh(self) -> None:
        if self._league is None:
            return
        evaluation = self._league.evaluation
        if not evaluation.has_log:
            self.summary_label.setText(
                f"Nu există încă un jurnal al predicțiilor pentru {self._league.name}. "
                "Rulează backtestul (aproximativ 10 secunde) ca să vezi comparația."
            )
            self.backtest_button.show()
            return
        self.backtest_button.hide()
        self._context.run_task(evaluation.results, self._show, self._results_failed)

    def _show(self, results: EvaluationResults) -> None:
        self._results = results
        self.summary_label.setText(
            f"{self._league.name}: {quantity(results.matches, 'meci', 'meciuri')}, sezoanele "
            f"{season_text(results.first_season)}–{season_text(results.last_season)}; fiecare "
            "model a prezis în ordine cronologică, doar din meciurile dinaintea fiecărei zile."
        )
        fill_table(
            self.metrics_table,
            [
                [
                    model_label(e.model),
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
                    f"{model_label(d.first)} – {model_label(d.second)}",
                    MEASURE_LABELS[d.measure],
                    signed(d.mean),
                    f"[{signed(d.lower)}; {signed(d.upper)}]",
                    model_label(d.better) if d.better else "nicio diferență reală",
                ]
                for d in results.differences
            ],
        )
        fill_table(
            self.agreement_table,
            [
                [
                    f"{model_label(a.first)} – {model_label(a.second)}",
                    percent(a.same_prediction),
                    number(a.mean_distance),
                ]
                for a in results.agreements
            ],
            fit=True,
        )
        self.agreement_label.setText(
            "Toate trei modelele prezic același rezultat în "
            f"{percent(results.all_agree)} dintre meciuri."
        )
        self._show_breakdown(self.breakdown_box.currentText())
        self.calibration_chart.show_figure(
            charts.calibration_chart(
                {e.model: e.calibration for e in results.evaluations if e.calibration is not None}
            )
        )
        chosen = self.confusion_box.currentData()
        self.confusion_box.blockSignals(True)
        self.confusion_box.clear()
        for evaluation in results.evaluations:
            self.confusion_box.addItem(model_label(evaluation.model), evaluation.model)
        index = self.confusion_box.findData(chosen) if chosen else 0
        self.confusion_box.setCurrentIndex(max(index, 0))
        self.confusion_box.blockSignals(False)
        self._show_confusion()

    def _show_confusion(self) -> None:
        model = self.confusion_box.currentData()
        if self._results is None or model is None:
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
                    subset_label(s.label),
                    str(s.matches),
                    *(
                        number(s.brier[model].value)
                        for model in (*COMPARED_MODELS, REFERENCE_MODEL)
                    ),
                    model_label(s.best),
                    "da" if s.lead is not None and s.lead.significant else "nu",
                ]
                for s in subsets
            ],
        )

    def _results_failed(self, message: str) -> None:
        # Shown in place rather than in a dialog: every change of screen would repeat a dialog.
        self.summary_label.setText(unreadable_log_text(message))
        self.backtest_button.show()

    def _run_backtest(self) -> None:
        self.backtest_button.setEnabled(False)
        self.summary_label.setText("Backtestul rulează…")
        self._context.run_task(self._league.evaluation.build_log, self._built, self._failed)

    def _built(self, _: object) -> None:
        self.backtest_button.setEnabled(True)
        self.refresh()

    def _failed(self, message: str) -> None:
        self.backtest_button.setEnabled(True)
        self._context.report_error(message)
        self.refresh()
