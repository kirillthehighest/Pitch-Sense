"""What every screen needs: the services of each league, the comparison of the leagues, the
user's preferences, the update of the season in progress, a task runner and a way to report
errors."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from PySide6.QtWidgets import QMessageBox

from app.data.competitions import competition
from app.data.paths import LIVE_DIR
from app.evaluation.backtesting import log_path
from app.services.catalog import DataCatalog, available_competitions
from app.services.evaluation import EvaluationService
from app.services.leagues import LeagueComparisonService
from app.services.predictions import PredictionService
from app.services.preferences import Preferences
from app.services.teams import TeamService
from app.services.updates import update_season
from app.ui.worker import Computer, Runner, compute_in_process, run_in_background


def show_error_dialog(message: str) -> None:
    QMessageBox.warning(None, "PitchSense", f"A apărut o problemă:\n\n{message}")


@dataclass(eq=False)
class LeagueServices:
    """The services of one league."""

    code: str
    name: str
    catalog: DataCatalog
    predictions: PredictionService
    teams: TeamService
    evaluation: EvaluationService


@dataclass(eq=False)
class AppContext:
    """The services shared by the screens. Tests pass a synchronous runner and collect errors.

    A league's services are opened the first time the league is shown and then kept, until
    ``reload`` drops them after an update of the season in progress.
    """

    competitions: tuple[str, ...]
    open_league: Callable[[str], LeagueServices]
    comparison: LeagueComparisonService
    preferences: Preferences
    update_data: Callable[[], Any] = update_season  # downloads; returns an UpdateSummary
    today: Callable[[], date] = date.today  # the matches screen opens on the next match day
    run_task: Runner = run_in_background
    compute: Computer = compute_in_process  # long computations, away from the window
    report_error: Callable[[str], None] = field(default=show_error_dialog)
    _leagues: dict[str, LeagueServices] = field(default_factory=dict, init=False, repr=False)

    def league(self, code: str) -> LeagueServices:
        if code not in self.competitions:
            raise ValueError(f"league {code!r} is not in the database")
        if code not in self._leagues:
            self._leagues[code] = self.open_league(code)
        return self._leagues[code]

    def reload(self) -> None:
        """Forget the opened leagues, so that they are read again with the new data."""
        self._leagues.clear()

    @property
    def first_league(self) -> str:
        """The league to show at start: the one shown last time, or else the first one."""
        remembered = self.preferences.competition
        return remembered if remembered in self.competitions else self.competitions[0]


def open_league(code: str) -> LeagueServices:
    """Load one league from the real database and its season in progress, when downloaded."""
    catalog = DataCatalog.load(competition=code, live_dir=LIVE_DIR)
    return LeagueServices(
        code=code,
        name=competition(code).name,
        catalog=catalog,
        predictions=PredictionService(catalog.matches, catalog.fixtures),
        teams=TeamService(catalog.matches, in_progress=catalog.current_season),
        evaluation=EvaluationService(log_path(code), competition=code),
    )


def default_context() -> AppContext:
    """The real data; raises FileNotFoundError when the database has not been built."""
    competitions = tuple(available_competitions())
    if not competitions:
        raise FileNotFoundError("The database holds no known league. Run the database build.")
    return AppContext(
        competitions=competitions,
        open_league=open_league,
        comparison=LeagueComparisonService(competitions),
        preferences=Preferences(),
    )
