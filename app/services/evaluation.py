"""Evaluation results for the user interface, read from the prediction log.

The log is written by the backtest (``python -m app.evaluation.backtesting``); ``build_log`` runs
it when the log is missing (about 8 s on the full data).
"""

from dataclasses import dataclass
from pathlib import Path

from app.data.paths import DATABASE_PATH
from app.data.repository import MatchRepository
from app.evaluation.backtesting import COMPETITION, log_path, read_log, run_backtest, write_log
from app.evaluation.bookmakers import BookmakerComparison, compare_with_bookmakers
from app.evaluation.comparison import (
    Agreement,
    PairedDifference,
    SubsetComparison,
    agreements,
    all_agree,
    by_matchup_type,
    by_outcome,
    by_season,
    paired_differences,
)
from app.evaluation.evaluator import ModelEvaluation, evaluate
from app.evaluation.periods import FIRST_EVALUATION_SEASON
from app.prediction.logistic_predictions import MIN_TRAINING_MATCHES


@dataclass(frozen=True, eq=False)
class EvaluationResults:
    """Everything the comparison screen shows."""

    matches: int
    first_season: str
    last_season: str
    evaluations: tuple[ModelEvaluation, ...]
    differences: tuple[PairedDifference, ...]
    by_season: tuple[SubsetComparison, ...]
    by_outcome: tuple[SubsetComparison, ...]
    by_matchup_type: tuple[SubsetComparison, ...]
    agreements: tuple[Agreement, ...]
    all_agree: float
    bookmakers: BookmakerComparison | None = None  # None without odds in the database


class EvaluationService:
    """Reads (and if needed builds) one league's prediction log and computes the results once."""

    def __init__(
        self,
        log: Path | None = None,
        database_path: Path = DATABASE_PATH,
        *,
        competition: str = COMPETITION,
        first_evaluation_season: str = FIRST_EVALUATION_SEASON,
        min_training_matches: int = MIN_TRAINING_MATCHES,
    ) -> None:
        self.log = log or log_path(competition)
        self.competition = competition
        self._database_path = database_path
        self._first_evaluation_season = first_evaluation_season
        self._min_training_matches = min_training_matches
        self._results: EvaluationResults | None = None

    @property
    def has_log(self) -> bool:
        return self.log.is_file()

    def build_log(self) -> None:
        """Run the backtest and write the log (the slow step)."""
        if not self._database_path.is_file():
            raise FileNotFoundError(
                f"Database not found: {self._database_path}. Run: python -m app.data.build_database"
            )
        with MatchRepository.open(self._database_path) as repository:
            backtest = run_backtest(
                repository.matches(self.competition),
                first_evaluation_season=self._first_evaluation_season,
                min_training_matches=self._min_training_matches,
            )
        write_log(backtest.rows, self.log)
        self._results = None

    def results(self) -> EvaluationResults:
        """The evaluation and comparison of the log, computed once."""
        if self._results is None:
            if not self.has_log:
                raise FileNotFoundError(
                    f"Prediction log not found: {self.log}. Run the backtest first."
                )
            try:
                rows = read_log(self.log)
                evaluations = evaluate(rows)
            except ValueError as error:
                raise ValueError(
                    f"The prediction log cannot be used: {error}. "
                    "Run the backtest again to rebuild it."
                ) from error
            seasons = sorted({row.season for row in rows})
            odds = []
            if self._database_path.is_file():
                with MatchRepository.open(self._database_path) as repository:
                    odds = repository.market_odds(self.competition)
            self._results = EvaluationResults(
                matches=evaluations[0].matches,
                first_season=seasons[0],
                last_season=seasons[-1],
                evaluations=tuple(evaluations),
                differences=tuple(paired_differences(rows)),
                by_season=tuple(by_season(rows)),
                by_outcome=tuple(by_outcome(rows)),
                by_matchup_type=tuple(by_matchup_type(rows)),
                agreements=tuple(agreements(rows)),
                all_agree=all_agree(rows),
                bookmakers=compare_with_bookmakers(self.competition, rows, odds),
            )
        return self._results
