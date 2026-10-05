"""Comparison of the leagues: their character and how the models do in each of them.

Run from the project folder with ``python -m app.evaluation.leagues`` after
``python -m app.evaluation.backtesting`` has written the log of every league.

For every league, over its evaluation seasons (2010/11-2025/26):

- character: the share of home wins, draws and away wins, goals per match, the home side's goal
  margin, and the home win rate in 2020/21 (played mostly behind closed doors in all five)
  against the other seasons;
- the models: the measures of ``evaluator`` and the Brier skill score against the "past
  frequencies" baseline, 1 - Brier(model) / Brier(baseline): the share of the baseline's error
  a model removes, which makes leagues with different amounts of randomness comparable;
- the ranking: the paired differences between the three models (``comparison``), per league and
  over all leagues pooled.
"""

import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from app.data.competitions import COMPETITIONS
from app.evaluation.backtesting import PAST_FREQUENCIES, PredictionLogRow, log_path, read_log
from app.evaluation.comparison import (
    COMPARED_MODELS,
    ELO,
    LOGISTIC,
    POISSON,
    Measure,
    PairedDifference,
    paired_differences,
)
from app.evaluation.evaluator import ModelEvaluation, evaluate

CLOSED_DOORS_SEASON = "2020-21"
MODEL_PAIRS = ((ELO, LOGISTIC), (ELO, POISSON), (LOGISTIC, POISSON))


@dataclass(frozen=True, slots=True)
class LeagueCharacter:
    """What the matches of one league looked like over the evaluation seasons."""

    competition: str
    matches: int
    home_win: float
    draw: float
    away_win: float
    goals: float  # per match
    home_margin: float  # home goals minus away goals per match
    closed_doors_home_win: float | None  # in 2020/21; None when the log has no such season
    other_seasons_home_win: float | None


@dataclass(frozen=True, eq=False)
class LeagueResults:
    """The models' results in one league."""

    competition: str
    character: LeagueCharacter
    evaluations: tuple[ModelEvaluation, ...]
    skill: Mapping[str, float]  # Brier skill score of each compared model against the baseline
    differences: tuple[PairedDifference, ...]  # Brier score, MODEL_PAIRS

    @property
    def best(self) -> str:
        """The compared model with the lowest Brier score."""
        brier = {e.model: e.brier.value for e in self.evaluations if e.model in COMPARED_MODELS}
        return min(brier, key=brier.__getitem__)


def league_character(
    competition: str,
    rows: Sequence[PredictionLogRow],
    closed_doors_season: str = CLOSED_DOORS_SEASON,
) -> LeagueCharacter:
    """Describe a league from its log (one row per match is enough: the baseline's)."""
    matches = [row for row in rows if row.model == PAST_FREQUENCIES]
    if not matches:
        raise ValueError(f"{competition}: the log has no matches")
    closed = [row for row in matches if row.season == closed_doors_season]
    others = [row for row in matches if row.season != closed_doors_season]
    if not closed or not others:  # the comparison needs both; without them it is not available
        closed = others = []
    count = len(matches)
    return LeagueCharacter(
        competition=competition,
        matches=count,
        home_win=_share(matches, "H"),
        draw=_share(matches, "D"),
        away_win=_share(matches, "A"),
        goals=math.fsum(row.home_goals + row.away_goals for row in matches) / count,
        home_margin=math.fsum(row.home_goals - row.away_goals for row in matches) / count,
        closed_doors_home_win=_share(closed, "H") if closed else None,
        other_seasons_home_win=_share(others, "H") if others else None,
    )


def league_results(
    competition: str,
    rows: Sequence[PredictionLogRow],
    closed_doors_season: str = CLOSED_DOORS_SEASON,
) -> LeagueResults:
    """Evaluate and rank the models of one league."""
    evaluations = evaluate(rows)
    baseline = next(e for e in evaluations if e.model == PAST_FREQUENCIES).brier.value
    skill = {
        e.model: 1 - e.brier.value / baseline for e in evaluations if e.model in COMPARED_MODELS
    }
    return LeagueResults(
        competition=competition,
        character=league_character(competition, rows, closed_doors_season),
        evaluations=tuple(evaluations),
        skill=skill,
        differences=_brier_differences(rows),
    )


def pooled_differences(logs: Mapping[str, Sequence[PredictionLogRow]]) -> list[PairedDifference]:
    """The paired Brier differences between the models over the matches of all leagues."""
    return list(_brier_differences([row for rows in logs.values() for row in rows]))


def main(
    competitions: Sequence[str] | None = None,
    results_dir: Path | None = None,
    closed_doors_season: str = CLOSED_DOORS_SEASON,
) -> int:
    """Print the comparison of the leagues (default: all five). The logs are read from
    ``results_dir`` (default: the project's results folder). Returns the process exit code."""
    codes = list(competitions or COMPETITIONS)
    logs: dict[str, list[PredictionLogRow]] = {}
    for code in codes:
        path = results_dir / log_path(code).name if results_dir else log_path(code)
        if not path.is_file():
            print(
                f"Prediction log not found: {path}\nRun: python -m app.evaluation.backtesting",
                file=sys.stderr,
            )
            return 1
        logs[code] = read_log(path)
    results = [league_results(code, rows, closed_doors_season) for code, rows in logs.items()]

    print("League character over the evaluation seasons (2010-11 to 2025-26)")
    print(f"{'league':16s} {'matches':>7s} {'home':>6s} {'draw':>6s} {'away':>6s} {'goals':>6s}"
          f" {'margin':>7s} {'home 20-21':>11s} {'home other':>11s}")  # fmt: skip
    for r in results:
        c = r.character
        print(
            f"{_name(r.competition):16s} {c.matches:7d} {c.home_win:6.1%} {c.draw:6.1%}"
            f" {c.away_win:6.1%} {c.goals:6.2f} {c.home_margin:+7.2f}"
            f" {_optional_share(c.closed_doors_home_win):>11s}"
            f" {_optional_share(c.other_seasons_home_win):>11s}"
        )

    print("\nModels per league (accuracy / Brier score / log loss; skill = 1 - Brier / baseline)")
    for r in results:
        cells = []
        for e in r.evaluations:
            if e.model in COMPARED_MODELS or e.model == PAST_FREQUENCIES:
                skill = f" skill {r.skill[e.model]:.3f}" if e.model in r.skill else ""
                cells.append(
                    f"{e.model}: {e.accuracy.value:.1%} / {e.brier.value:.4f}"
                    f" / {e.log_loss.value:.4f}{skill}"
                )
        print(f"  {_name(r.competition)} (best: {r.best})")
        for cell in cells:
            print(f"    {cell}")

    print("\nPaired Brier differences (first minus second, 95% interval)")
    for r in results:
        print(f"  {_name(r.competition)}")
        _print_differences(r.differences)
    print(f"  All leagues pooled ({sum(r.character.matches for r in results)} matches)")
    _print_differences(pooled_differences(logs))
    return 0


def _brier_differences(rows: Sequence[PredictionLogRow]) -> tuple[PairedDifference, ...]:
    return tuple(
        difference
        for difference in paired_differences(rows, MODEL_PAIRS)
        if difference.measure is Measure.BRIER
    )


def _optional_share(value: float | None) -> str:
    return "-" if value is None else f"{value:.1%}"


def _share(rows: Sequence[PredictionLogRow], outcome: str) -> float:
    return sum(row.actual == outcome for row in rows) / len(rows)


def _name(code: str) -> str:
    return COMPETITIONS[code].name if code in COMPETITIONS else code


def _print_differences(differences: Sequence[PairedDifference]) -> None:
    for d in differences:
        verdict = d.better or "no real difference"
        print(
            f"    {d.first:20s} vs {d.second:20s} {d.mean:+.4f} [{d.lower:+.4f}, {d.upper:+.4f}]"
            f"  {verdict}"
        )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
