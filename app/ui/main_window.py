"""The main window: four tabs over the shared services, and the application entry point."""

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget

from app.data.paths import copy_bundled_results
from app.ui.algorithm_comparison import AlgorithmComparisonTab
from app.ui.context import AppContext, default_context
from app.ui.dashboard import DashboardTab
from app.ui.match_prediction import MatchPredictionTab
from app.ui.team_analysis import TeamAnalysisTab

WINDOW_TITLE = "PitchSense - football analytics and match prediction"


class MainWindow(QMainWindow):
    """Hosts the tabs and prepares the historical predictions in the background."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1200, 800)

        self.dashboard = DashboardTab(context)
        self.match_prediction = MatchPredictionTab(context)
        self.team_analysis = TeamAnalysisTab(context)
        self.algorithm_comparison = AlgorithmComparisonTab(context)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.match_prediction, "Match Prediction")
        self.tabs.addTab(self.team_analysis, "Team Analysis")
        self.tabs.addTab(self.algorithm_comparison, "Algorithm Comparison")
        self.tabs.currentChanged.connect(self._tab_changed)
        self.setCentralWidget(self.tabs)
        self.prepare_predictions()

    def prepare_predictions(self) -> None:
        """Predict all real matches once, so that played matches are answered instantly."""
        predictions = self._context.predictions
        if predictions.is_prepared:
            self.statusBar().showMessage("Predictions ready")
            return
        self.statusBar().showMessage("Preparing the predictions for all matches...")
        self._context.run_task(predictions.prepare, self._predictions_ready, self._failed)

    def _predictions_ready(self, _: object) -> None:
        self.statusBar().showMessage("Predictions ready", 5000)

    def _failed(self, message: str) -> None:
        self.statusBar().clearMessage()
        self._context.report_error(message)

    def _tab_changed(self, _: int) -> None:
        # The log may have been built from another tab; both views read the same cached results.
        self.dashboard.refresh()
        self.algorithm_comparison.refresh()


def main() -> int:
    """Start the application; returns the exit code."""
    application = QApplication.instance() or QApplication(sys.argv)
    try:
        copy_bundled_results()  # a packaged application ships its prediction log read-only
    except OSError as error:  # without the copy the log can still be rebuilt in the window
        QMessageBox.warning(None, "PitchSense", f"Could not copy the prediction log: {error}")
    try:
        context = default_context()
    except FileNotFoundError as error:
        QMessageBox.critical(None, "PitchSense", str(error))
        return 1
    window = MainWindow(context)
    window.show()
    return application.exec()
