"""What every screen needs: the services, a task runner and a way to report errors."""

from collections.abc import Callable
from dataclasses import dataclass, field

from PySide6.QtWidgets import QMessageBox

from app.services.catalog import DataCatalog
from app.services.evaluation import EvaluationService
from app.services.predictions import PredictionService
from app.services.teams import TeamService
from app.ui.worker import Runner, run_in_background


def show_error_dialog(message: str) -> None:
    QMessageBox.warning(None, "PitchSense", message)


@dataclass
class AppContext:
    """The services shared by the screens. Tests pass a synchronous runner and collect errors."""

    catalog: DataCatalog
    predictions: PredictionService
    teams: TeamService
    evaluation: EvaluationService
    run_task: Runner = run_in_background
    report_error: Callable[[str], None] = field(default=show_error_dialog)


def default_context() -> AppContext:
    """Load the real data; raises FileNotFoundError when the database has not been built."""
    catalog = DataCatalog.load()
    return AppContext(
        catalog=catalog,
        predictions=PredictionService(catalog.matches),
        teams=TeamService(catalog.matches),
        evaluation=EvaluationService(),
    )
