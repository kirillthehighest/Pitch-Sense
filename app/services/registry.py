"""The services of each league, opened from the real data, as the local server of the web
interface keeps them (Phase 22)."""

from dataclasses import dataclass

from app.data.competitions import competition
from app.data.paths import LIVE_DIR
from app.evaluation.backtesting import log_path
from app.services.catalog import DataCatalog
from app.services.evaluation import EvaluationService
from app.services.predictions import PredictionService
from app.services.teams import TeamService


@dataclass(eq=False)
class LeagueServices:
    """The services of one league."""

    code: str
    name: str
    catalog: DataCatalog
    predictions: PredictionService
    teams: TeamService
    evaluation: EvaluationService


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
