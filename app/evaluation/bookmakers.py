"""The models measured against the bookmakers (Phase 23).

Run from the project folder with ``python -m app.evaluation.bookmakers [CODE ...]`` after the
backtest has written the logs and the database holds the odds (``app/data/odds.py``).

The bookmakers' average odds of each evaluation match, collected before kickoff, become a
reference forecast, "Bookmakers", with the margin removed proportionally. It is scored with the
same metrics as the models and compared match by match on the evaluation matches that have odds
(nearly all). The odds are never an input of a model: the models' predictions are those of the
prediction log, made before the odds are read.
"""

import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from app.data.competitions import COMPETITIONS, competition
from app.data.odds import MarketOdds, odds_by_match
from app.data.paths import DATABASE_PATH
from app.data.repository import MatchRepository
from app.evaluation.backtesting import PAST_FREQUENCIES, PredictionLogRow, log_path, read_log
from app.evaluation.comparison import COMPARED_MODELS, Measure, PairedDifference, paired_differences
from app.evaluation.evaluator import ModelEvaluation, evaluate
from app.prediction.outputs import OutcomeProbabilities

BOOKMAKERS = "Bookmakers"


@dataclass(frozen=True, eq=False)
class BookmakerComparison:
    """The models and the bookmakers on the evaluation matches with odds."""

    competition: str
    matches: int  # evaluation matches with odds
    missing: int  # evaluation matches without
    evaluations: tuple[ModelEvaluation, ...]  # the log's models, then the bookmakers
    differences: tuple[PairedDifference, ...]  # Brier score, each compared model minus them

    @property
    def bookmakers(self) -> ModelEvaluation:
        return next(e for e in self.evaluations if e.model == BOOKMAKERS)


def bookmaker_rows(
    rows: Sequence[PredictionLogRow], odds: Mapping[tuple[date, str, str], MarketOdds]
) -> list[PredictionLogRow]:
    """One "Bookmakers" row for every match of the log that has odds."""
    seen, found = set(), []
    for row in rows:
        key = (row.match_date, row.home_team, row.away_team)
        if key in seen or key not in odds:
            continue
        seen.add(key)
        implied = OutcomeProbabilities(*odds[key].probabilities())
        found.append(
            replace(
                row,
                model=BOOKMAKERS,
                p_home=implied.home_win,
                p_draw=implied.draw,
                p_away=implied.away_win,
                predicted=implied.most_likely.value,
                expected_home_goals=None,
                expected_away_goals=None,
            )
        )
    return found


def compare_with_bookmakers(
    code: str, rows: Sequence[PredictionLogRow], odds: Iterable[MarketOdds]
) -> BookmakerComparison | None:
    """The comparison of a league's log with the bookmakers; None without odds for its
    matches (a database built before Phase 23)."""
    reference = bookmaker_rows(rows, odds_by_match(list(odds)))
    if not reference:
        return None
    covered = {(r.match_date, r.home_team, r.away_team) for r in reference}
    kept = [r for r in rows if (r.match_date, r.home_team, r.away_team) in covered]
    total = len({(r.match_date, r.home_team, r.away_team) for r in rows})
    combined = [*kept, *reference]
    compared = [m for m in (*COMPARED_MODELS, PAST_FREQUENCIES) if any(r.model == m for r in kept)]
    differences = [
        d
        for d in paired_differences(combined, [(model, BOOKMAKERS) for model in compared])
        if d.measure == Measure.BRIER
    ]
    return BookmakerComparison(
        competition=code,
        matches=len(covered),
        missing=total - len(covered),
        evaluations=tuple(evaluate(combined)),
        differences=tuple(differences),
    )


def main(competitions: Sequence[str] | None = None, database_path: Path = DATABASE_PATH) -> int:
    """Print every league's comparison with the bookmakers. Returns the process exit code."""
    if not database_path.is_file():
        print(
            f"Database not found: {database_path}\nRun: python -m app.data.build_database",
            file=sys.stderr,
        )
        return 1
    for code in competitions or COMPETITIONS:
        log = log_path(code)
        if not log.is_file():
            print(
                f"Prediction log not found: {log}\nRun: python -m app.evaluation.backtesting",
                file=sys.stderr,
            )
            return 1
        with MatchRepository.open(database_path) as repository:
            odds = repository.market_odds(code)
        result = compare_with_bookmakers(code, read_log(log), odds)
        print(f"\n{competition(code).name}")
        if result is None:
            print("  no odds in the database; rebuild it: python -m app.data.build_database")
            continue
        print(f"  {result.matches} evaluation matches with odds ({result.missing} without)")
        for e in result.evaluations:
            if e.brier is None:
                continue
            sure = next((c for c in e.confident if c.threshold == 0.65), None)
            sure_text = (
                f"{sure.accuracy.value:.1%} of {sure.matches}" if sure and sure.accuracy else "-"
            )
            print(
                f"  {e.model:22s} accuracy {e.accuracy.value:.1%}  Brier {e.brier.value:.4f}"
                f"  log loss {e.log_loss.value:.4f}  at 65%+: {sure_text}"
            )
        for d in result.differences:
            verdict = d.better or "no real difference"
            print(
                f"  {d.first:22s} - Bookmakers  {d.mean:+.4f} [{d.lower:+.4f}, {d.upper:+.4f}]"
                f"  {verdict}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
