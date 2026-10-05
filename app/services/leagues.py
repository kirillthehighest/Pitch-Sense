"""The comparison of the leagues, for the "Ligi" screen.

Reads the prediction log of every league in the database and computes, once, what
``app/evaluation/leagues.py`` reports: each league's character and results, and the ranking of
the models over all leagues together. Leagues without a log can be backtested from here.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.data.paths import DATABASE_PATH, RESULTS_DIR
from app.data.repository import MatchRepository
from app.evaluation.backtesting import log_path, read_log, run_backtest, write_log
from app.evaluation.comparison import PairedDifference
from app.evaluation.leagues import (
    CLOSED_DOORS_SEASON,
    LeagueResults,
    league_results,
    pooled_differences,
)
from app.evaluation.periods import FIRST_EVALUATION_SEASON
from app.prediction.logistic_predictions import MIN_TRAINING_MATCHES


@dataclass(frozen=True, eq=False)
class LeaguesOverview:
    """Everything the leagues screen shows."""

    results: tuple[LeagueResults, ...]  # in the order of the competitions given
    pooled: tuple[PairedDifference, ...]  # Brier differences over all leagues together
    matches: int  # evaluation matches over all leagues


class LeagueComparisonService:
    """Compares the leagues whose prediction logs exist; can build the missing logs."""

    def __init__(
        self,
        competitions: Sequence[str],
        results_dir: Path = RESULTS_DIR,
        database_path: Path = DATABASE_PATH,
        *,
        first_evaluation_season: str = FIRST_EVALUATION_SEASON,
        min_training_matches: int = MIN_TRAINING_MATCHES,
        closed_doors_season: str = CLOSED_DOORS_SEASON,
    ) -> None:
        self.competitions = tuple(competitions)
        self._results_dir = results_dir
        self._database_path = database_path
        self._first_evaluation_season = first_evaluation_season
        self._min_training_matches = min_training_matches
        self._closed_doors_season = closed_doors_season
        self._overview: LeaguesOverview | None = None

    def log(self, code: str) -> Path:
        return self._results_dir / log_path(code).name

    def missing(self) -> list[str]:
        """The leagues that have no prediction log yet."""
        return [code for code in self.competitions if not self.log(code).is_file()]

    def build_missing_logs(self) -> None:
        """Run the backtest of every league without a log (the slow step, about 10 s each)."""
        if not self._database_path.is_file():
            raise FileNotFoundError(
                f"Database not found: {self._database_path}. Run: python -m app.data.build_database"
            )
        with MatchRepository.open(self._database_path) as repository:
            for code in self.missing():
                backtest = run_backtest(
                    repository.matches(code),
                    first_evaluation_season=self._first_evaluation_season,
                    min_training_matches=self._min_training_matches,
                )
                write_log(backtest.rows, self.log(code))
        self._overview = None

    def overview(self) -> LeaguesOverview:
        """The comparison of all leagues, computed once; every league needs its log."""
        if self._overview is None:
            missing = self.missing()
            if missing:
                raise FileNotFoundError(
                    f"Prediction logs missing for {', '.join(missing)}. Run the backtest first."
                )
            logs = {code: read_log(self.log(code)) for code in self.competitions}
            results = tuple(
                league_results(code, rows, self._closed_doors_season) for code, rows in logs.items()
            )
            self._overview = LeaguesOverview(
                results=results,
                pooled=tuple(pooled_differences(logs)),
                matches=sum(result.character.matches for result in results),
            )
        return self._overview
