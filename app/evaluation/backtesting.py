"""Chronological (walk-forward) backtesting: the prediction log of the evaluation seasons.

Run from the project folder with ``python -m app.evaluation.backtesting``.

Every model predicts every match from data before the match's day (see the prediction engine).
The log keeps only the evaluation seasons and only matches that all three models predicted, so
they are compared under identical conditions. Two reference baselines are added:

- "Past frequencies": the league's home win, draw and away win frequencies over the last 380
  matches before the day; a full probability forecast.
- "Always home win": probability 1 for a home win. It serves as a reference for accuracy only,
  because its zero probabilities cannot be scored by probability measures such as log loss.

Each row also carries both teams' point-in-time K-Means groups (0 = strongest, "promoted" for
teams without a previous season), for the comparison by type of match.
"""

import csv
import sys
import time
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import astuple, dataclass, fields
from datetime import date
from pathlib import Path

from app.data.models import Match
from app.data.paths import DATABASE_PATH, RESULTS_DIR
from app.data.preprocessing import sort_chronologically
from app.data.repository import MatchRepository
from app.evaluation.periods import FIRST_EVALUATION_SEASON
from app.evaluation.team_clustering import point_in_time_groups
from app.prediction.logistic_predictions import MIN_TRAINING_MATCHES
from app.prediction.outputs import ModelName, OutcomeProbabilities
from app.prediction.poisson_predictions import LEAGUE_WINDOW
from app.prediction.prediction_engine import predict_history
from app.statistics.team_statistics import MatchHistory, league_averages

COMPETITION = "SP1"
PAST_FREQUENCIES = "Past frequencies"
ALWAYS_HOME_WIN = "Always home win"
MODEL_ORDER = (*(str(model) for model in ModelName), PAST_FREQUENCIES, ALWAYS_HOME_WIN)
PROMOTED = "promoted"


@dataclass(frozen=True, slots=True)
class PredictionLogRow:
    """One model's prediction for one evaluation match, with the match's real result."""

    match_date: date
    season: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    actual: str
    model: str
    p_home: float
    p_draw: float
    p_away: float
    predicted: str
    expected_home_goals: float | None
    expected_away_goals: float | None
    home_group: str
    away_group: str


@dataclass(frozen=True, slots=True)
class Backtest:
    """The prediction log and the evaluation matches left out because a model was missing."""

    rows: tuple[PredictionLogRow, ...]
    excluded_matches: int


def run_backtest(
    matches: Iterable[Match],
    *,
    first_evaluation_season: str = FIRST_EVALUATION_SEASON,
    min_training_matches: int = MIN_TRAINING_MATCHES,
) -> Backtest:
    """Predict all matches walk-forward and log those of the evaluation seasons."""
    ordered = sort_chronologically(matches)
    history = MatchHistory(ordered)
    groups_by_season: dict[str, dict[str, int | None]] = {}
    rows: list[PredictionLogRow] = []
    excluded = 0
    for result in predict_history(ordered, min_training_matches=min_training_matches):
        match = result.match
        if match.season < first_evaluation_season:
            continue
        if not result.has_all_models:
            excluded += 1
            continue
        if match.season not in groups_by_season:
            groups_by_season[match.season] = point_in_time_groups(history, match.season)
        groups = groups_by_season[match.season]
        forecasts: list[tuple[str, OutcomeProbabilities, tuple[float, float] | None]] = [
            (str(model), prediction.probabilities, prediction.expected_goals)
            for model, prediction in result.predictions.items()
        ]
        forecasts.append((PAST_FREQUENCIES, _past_frequencies(history, match.match_date), None))
        forecasts.append((ALWAYS_HOME_WIN, OutcomeProbabilities(1.0, 0.0, 0.0), None))
        for model, probabilities, expected_goals in forecasts:
            rows.append(
                PredictionLogRow(
                    match_date=match.match_date,
                    season=match.season,
                    home_team=match.home_team,
                    away_team=match.away_team,
                    home_goals=match.home_goals,
                    away_goals=match.away_goals,
                    actual=match.result.value,
                    model=model,
                    p_home=probabilities.home_win,
                    p_draw=probabilities.draw,
                    p_away=probabilities.away_win,
                    predicted=probabilities.most_likely.value,
                    expected_home_goals=expected_goals[0] if expected_goals else None,
                    expected_away_goals=expected_goals[1] if expected_goals else None,
                    home_group=_group_label(groups[match.home_team]),
                    away_group=_group_label(groups[match.away_team]),
                )
            )
    return Backtest(rows=tuple(rows), excluded_matches=excluded)


def write_log(rows: Sequence[PredictionLogRow], path: Path) -> None:
    """Save the log as CSV; probabilities keep their full precision."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(field.name for field in fields(PredictionLogRow))
        for row in rows:
            writer.writerow("" if value is None else _text(value) for value in astuple(row))


def read_log(path: Path) -> list[PredictionLogRow]:
    """Load a log written by ``write_log``; a damaged file raises ValueError naming the line."""
    columns = [field.name for field in fields(PredictionLogRow)]
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"{path.name} is empty")
        missing = [column for column in columns if column not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"{path.name} is not a prediction log: missing columns {', '.join(missing)}"
            )
        rows = []
        for record in reader:
            line = f"{path.name}, line {reader.line_num}"
            if None in record or None in record.values():  # too many or too few values
                raise ValueError(f"{line}: expected {len(reader.fieldnames)} values")
            try:
                rows.append(_row_from_text(record))
            except ValueError as error:
                raise ValueError(f"{line}: {error}") from error
        return rows


def log_path(competition: str = COMPETITION) -> Path:
    return RESULTS_DIR / f"backtest_{competition}.csv"


def main(
    database_path: Path = DATABASE_PATH,
    output: Path | None = None,
    *,
    first_evaluation_season: str = FIRST_EVALUATION_SEASON,
    min_training_matches: int = MIN_TRAINING_MATCHES,
) -> int:
    """Run the backtest, save the log and print a summary. Returns the process exit code."""
    if not database_path.is_file():
        print(
            f"Database not found: {database_path}\nRun: python -m app.data.build_database",
            file=sys.stderr,
        )
        return 1
    output = output or log_path()
    started = time.perf_counter()
    with MatchRepository.open(database_path) as repository:
        backtest = run_backtest(
            repository.matches(COMPETITION),
            first_evaluation_season=first_evaluation_season,
            min_training_matches=min_training_matches,
        )
    if not backtest.rows:
        print(f"No evaluation matches from {first_evaluation_season} on", file=sys.stderr)
        return 1
    write_log(backtest.rows, output)
    seconds = time.perf_counter() - started
    per_model = Counter(row.model for row in backtest.rows)
    seasons = sorted({row.season for row in backtest.rows})
    matches = per_model[MODEL_ORDER[0]]
    print(f"Backtest on {COMPETITION}: {matches} matches, seasons {seasons[0]} to {seasons[-1]}")
    print(f"Matches left out because a model had no prediction: {backtest.excluded_matches}")
    for model in MODEL_ORDER:
        print(f"  {model}: {per_model[model]} predictions")
    print(f"Log written to {output} ({len(backtest.rows)} rows) in {seconds:.1f} s")
    return 0


def _past_frequencies(history: MatchHistory, before: date) -> OutcomeProbabilities:
    league = league_averages(history, before, last=LEAGUE_WINDOW)
    if not league.matches:
        raise ValueError(f"no league matches before {before} for the frequency baseline")
    return OutcomeProbabilities(league.home_win_rate, league.draw_rate, league.away_win_rate)


def _group_label(group: int | None) -> str:
    return PROMOTED if group is None else str(group)


def _text(value: object) -> str:
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _row_from_text(record: dict[str, str]) -> PredictionLogRow:
    def optional_float(text: str) -> float | None:
        return float(text) if text else None

    return PredictionLogRow(
        match_date=date.fromisoformat(record["match_date"]),
        season=record["season"],
        home_team=record["home_team"],
        away_team=record["away_team"],
        home_goals=int(record["home_goals"]),
        away_goals=int(record["away_goals"]),
        actual=record["actual"],
        model=record["model"],
        p_home=float(record["p_home"]),
        p_draw=float(record["p_draw"]),
        p_away=float(record["p_away"]),
        predicted=record["predicted"],
        expected_home_goals=optional_float(record["expected_home_goals"]),
        expected_away_goals=optional_float(record["expected_away_goals"]),
        home_group=record["home_group"],
        away_group=record["away_group"],
    )


if __name__ == "__main__":
    sys.exit(main())
