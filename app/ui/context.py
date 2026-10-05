"""What every screen needs: the services of each league, the comparison of the leagues, the
user's preferences, a task runner and a way to report errors."""

from collections.abc import Callable
from dataclasses import dataclass, field

from PySide6.QtWidgets import QMessageBox

from app.data.competitions import competition
from app.evaluation.backtesting import log_path
from app.services.catalog import DataCatalog, available_competitions
from app.services.evaluation import EvaluationService
from app.services.leagues import LeagueComparisonService
from app.services.predictions import PredictionService
from app.services.preferences import Preferences
from app.services.teams import TeamService
from app.ui.worker import Runner, run_in_background


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

    A league's services are opened the first time the league is shown and then kept.
    """

    competitions: tuple[str, ...]
    open_league: Callable[[str], LeagueServices]
    comparison: LeagueComparisonService
    preferences: Preferences
    run_task: Runner = run_in_background
    report_error: Callable[[str], None] = field(default=show_error_dialog)
    _leagues: dict[str, LeagueServices] = field(default_factory=dict, init=False, repr=False)

    def league(self, code: str) -> LeagueServices:
        if code not in self.competitions:
            raise ValueError(f"league {code!r} is not in the database")
        if code not in self._leagues:
            self._leagues[code] = self.open_league(code)
        return self._leagues[code]

    @property
    def first_league(self) -> str:
        """The league to show at start: the one shown last time, or else the first one."""
        remembered = self.preferences.competition
        return remembered if remembered in self.competitions else self.competitions[0]


def open_league(code: str) -> LeagueServices:
    """Load one league from the real database."""
    catalog = DataCatalog.load(competition=code)
    return LeagueServices(
        code=code,
        name=competition(code).name,
        catalog=catalog,
        predictions=PredictionService(catalog.matches),
        teams=TeamService(catalog.matches),
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
