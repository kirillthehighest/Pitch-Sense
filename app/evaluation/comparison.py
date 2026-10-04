"""Comparison of the algorithms on the same matches.

Run from the project folder with ``python -m app.evaluation.comparison`` after
``python -m app.evaluation.backtesting`` has written the log.

Paired differences: for two models A and B and one measure, d_i = score_A(i) - score_B(i) on every
match i. The mean of d has the standard error sd(d) / sqrt(n) and the 95% interval
mean +- 1.96 * standard error. Because both models are scored on the same matches, what is common
to them (how predictable each match was) cancels out, which makes the comparison much more
precise than putting two separate averages side by side. A difference is called real only when
its interval excludes 0.

Breakdowns: the same comparison within subsets of matches (by season, by actual result, by the
point-in-time K-Means groups of the two teams), to see where each model does well. In every
subset the best of the three models is the one with the lowest Brier score, and its lead over the
runner-up is tested with a paired difference inside the subset.

Agreement: how often two models predict the same most likely outcome, and how far apart their
forecasts are, measured by the total variation distance (1/2) sum_c |p_c - q_c|: the share of
probability that has to move to turn one forecast into the other (0 = identical, 1 = opposite).
"""

import math
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np

from app.evaluation.backtesting import (
    PAST_FREQUENCIES,
    PROMOTED,
    PredictionLogRow,
    log_path,
    read_log,
)
from app.evaluation.metrics import (
    OUTCOME_CODES,
    Estimate,
    brier_per_match,
    correct_per_match,
    estimate,
    log_loss_per_match,
    outcome_indices,
)
from app.prediction.outputs import ModelName

Z_95 = 1.96
ELO, POISSON, LOGISTIC = (str(model) for model in ModelName)
COMPARED_MODELS = (ELO, POISSON, LOGISTIC)
REFERENCE_MODEL = PAST_FREQUENCIES
MIN_GROUP_PAIR_MATCHES = 100
DEFAULT_DISAGREEMENTS = 5
MATCHUP_TYPES = (
    "promoted team involved",
    "elite team involved",
    "same group",
    "different groups",
)
DEFAULT_PAIRS = (
    (ELO, POISSON),
    (ELO, LOGISTIC),
    (POISSON, LOGISTIC),
    (ELO, PAST_FREQUENCIES),
    (POISSON, PAST_FREQUENCIES),
    (LOGISTIC, PAST_FREQUENCIES),
)


class Measure(StrEnum):
    """The per-match measures that are compared."""

    BRIER = "Brier score"
    LOG_LOSS = "log loss"
    ACCURACY = "accuracy"

    @property
    def lower_is_better(self) -> bool:
        return self is not Measure.ACCURACY


@dataclass(frozen=True, slots=True)
class PairedDifference:
    """The mean per-match difference first - second for one measure, with its 95% interval."""

    first: str
    second: str
    measure: Measure
    mean: float
    standard_error: float
    lower: float
    upper: float
    matches: int

    @property
    def significant(self) -> bool:
        """True when the 95% interval does not contain 0."""
        return self.lower > 0 or self.upper < 0

    @property
    def better(self) -> str | None:
        """The model that is really better on this measure; None when they cannot be told apart."""
        if not self.significant:
            return None
        first_lower = self.mean < 0
        return self.first if first_lower == self.measure.lower_is_better else self.second


@dataclass(frozen=True, eq=False)
class SubsetComparison:
    """The models compared within one subset of matches."""

    label: str
    matches: int
    brier: Mapping[str, Estimate]
    accuracy: Mapping[str, Estimate]
    best: str
    runner_up: str
    lead: PairedDifference | None  # best minus runner-up Brier score; None for a single match


@dataclass(frozen=True, slots=True)
class Agreement:
    """How similar two models' forecasts are over the same matches."""

    first: str
    second: str
    matches: int
    same_prediction: float
    mean_distance: float


@dataclass(frozen=True, slots=True)
class Disagreement:
    """A match on which the compared models' forecasts are far apart."""

    row: PredictionLogRow  # the match, taken from the first compared model's row
    forecasts: Mapping[str, tuple[float, float, float]]
    largest_distance: float


def total_variation_distance(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    """(1/2) sum_c |p_c - q_c| for every pair of forecast rows."""
    return 0.5 * np.abs(np.asarray(first, dtype=float) - np.asarray(second, dtype=float)).sum(
        axis=1
    )


def per_match_scores(rows: Sequence[PredictionLogRow]) -> dict[str, dict[Measure, np.ndarray]]:
    """Every model's per-match values of every measure, aligned on the same match order.

    Models that give probability 0 to some outcome (Always home win) get only accuracy.
    """
    by_model = _rows_by_model(rows)
    keys = sorted(next(iter(by_model.values())))
    scores = {}
    for model, model_rows in by_model.items():
        ordered = [model_rows[key] for key in keys]
        probabilities = np.array([[r.p_home, r.p_draw, r.p_away] for r in ordered])
        actual = outcome_indices([r.actual for r in ordered])
        model_scores = {Measure.ACCURACY: correct_per_match(probabilities, actual)}
        if (probabilities > 0).all():
            model_scores[Measure.BRIER] = brier_per_match(probabilities, actual)
            model_scores[Measure.LOG_LOSS] = log_loss_per_match(probabilities, actual)
        scores[model] = model_scores
    return scores


def paired_difference(
    first: np.ndarray, second: np.ndarray, first_name: str, second_name: str, measure: Measure
) -> PairedDifference:
    """The mean of first - second over the same matches, with its standard error and interval."""
    differences = np.asarray(first, dtype=float) - np.asarray(second, dtype=float)
    if differences.ndim != 1 or differences.size < 2:
        raise ValueError("need per-match values of at least two matches, in the same order")
    mean = float(differences.mean())
    standard_error = float(differences.std(ddof=1) / math.sqrt(differences.size))
    return PairedDifference(
        first=first_name,
        second=second_name,
        measure=measure,
        mean=mean,
        standard_error=standard_error,
        lower=mean - Z_95 * standard_error,
        upper=mean + Z_95 * standard_error,
        matches=differences.size,
    )


def paired_differences(
    rows: Sequence[PredictionLogRow], pairs: Sequence[tuple[str, str]] = DEFAULT_PAIRS
) -> list[PairedDifference]:
    """Compare every pair of models on every measure both of them have."""
    scores = per_match_scores(rows)
    results = []
    for first, second in pairs:
        for name in (first, second):
            if name not in scores:
                raise ValueError(f"model {name!r} is not in the log")
        for measure in Measure:
            if measure in scores[first] and measure in scores[second]:
                results.append(
                    paired_difference(
                        scores[first][measure], scores[second][measure], first, second, measure
                    )
                )
    return results


def matchup_type(home_group: str, away_group: str) -> str:
    """Classify a match by the teams' point-in-time groups, checking the types in order."""
    if PROMOTED in (home_group, away_group):
        return MATCHUP_TYPES[0]
    if "0" in (home_group, away_group):
        return MATCHUP_TYPES[1]
    if home_group == away_group:
        return MATCHUP_TYPES[2]
    return MATCHUP_TYPES[3]


def breakdown(
    rows: Sequence[PredictionLogRow],
    label_of: Callable[[PredictionLogRow], str],
    *,
    order: Sequence[str] | None = None,
    min_matches: int = 1,
) -> list[SubsetComparison]:
    """Compare the models within every subset of matches sharing a label.

    Subsets with fewer than ``min_matches`` matches are left out. Labels follow ``order`` when it
    is given, otherwise they are sorted.
    """
    scores = per_match_scores(rows)
    for model in (*COMPARED_MODELS, REFERENCE_MODEL):
        if model not in scores:
            raise ValueError(f"model {model!r} is not in the log")
    by_model = _rows_by_model(rows)
    reference_rows = by_model[COMPARED_MODELS[0]]
    labels = np.array([label_of(reference_rows[key]) for key in sorted(reference_rows)])
    present = set(labels.tolist())
    ordered_labels = [label for label in (order or sorted(present)) if label in present]

    comparisons = []
    for label in ordered_labels:
        inside = labels == label
        count = int(inside.sum())
        if count < min_matches:
            continue
        models = (*COMPARED_MODELS, REFERENCE_MODEL)
        brier = {model: estimate(scores[model][Measure.BRIER][inside]) for model in models}
        accuracy = {model: estimate(scores[model][Measure.ACCURACY][inside]) for model in models}
        best, runner_up = sorted(COMPARED_MODELS, key=lambda model: brier[model].value)[:2]
        lead = None
        if count >= 2:
            lead = paired_difference(
                scores[best][Measure.BRIER][inside],
                scores[runner_up][Measure.BRIER][inside],
                best,
                runner_up,
                Measure.BRIER,
            )
        comparisons.append(
            SubsetComparison(
                label=label,
                matches=count,
                brier=brier,
                accuracy=accuracy,
                best=best,
                runner_up=runner_up,
                lead=lead,
            )
        )
    return comparisons


def by_season(rows: Sequence[PredictionLogRow]) -> list[SubsetComparison]:
    return breakdown(rows, lambda row: row.season)


def by_outcome(rows: Sequence[PredictionLogRow]) -> list[SubsetComparison]:
    return breakdown(rows, lambda row: row.actual, order=OUTCOME_CODES)


def by_matchup_type(rows: Sequence[PredictionLogRow]) -> list[SubsetComparison]:
    return breakdown(
        rows, lambda row: matchup_type(row.home_group, row.away_group), order=MATCHUP_TYPES
    )


def by_group_pair(
    rows: Sequence[PredictionLogRow], min_matches: int = MIN_GROUP_PAIR_MATCHES
) -> list[SubsetComparison]:
    return breakdown(
        rows, lambda row: f"{row.home_group} v {row.away_group}", min_matches=min_matches
    )


def agreements(
    rows: Sequence[PredictionLogRow], models: Sequence[str] = COMPARED_MODELS
) -> list[Agreement]:
    """Compare the forecasts of every pair of the given models."""
    forecasts, predictions = _forecasts(rows, models)
    results = []
    for index, first in enumerate(models):
        for second in models[index + 1 :]:
            results.append(
                Agreement(
                    first=first,
                    second=second,
                    matches=len(predictions[first]),
                    same_prediction=float(np.mean(predictions[first] == predictions[second])),
                    mean_distance=float(
                        total_variation_distance(forecasts[first], forecasts[second]).mean()
                    ),
                )
            )
    return results


def all_agree(rows: Sequence[PredictionLogRow], models: Sequence[str] = COMPARED_MODELS) -> float:
    """The share of matches on which all the given models predict the same outcome."""
    _, predictions = _forecasts(rows, models)
    stacked = np.array([predictions[model] for model in models])
    return float(np.mean((stacked == stacked[0]).all(axis=0)))


def largest_disagreements(
    rows: Sequence[PredictionLogRow],
    count: int = DEFAULT_DISAGREEMENTS,
    models: Sequence[str] = COMPARED_MODELS,
) -> list[Disagreement]:
    """The matches with the largest distance between any two of the given models."""
    forecasts, _ = _forecasts(rows, models)
    largest = np.zeros(len(next(iter(forecasts.values()))))
    for index, first in enumerate(models):
        for second in models[index + 1 :]:
            distance = total_variation_distance(forecasts[first], forecasts[second])
            largest = np.maximum(largest, distance)
    reference = _rows_by_model(rows)[models[0]]
    keys = sorted(reference)
    order = np.argsort(-largest, kind="stable")[:count]
    return [
        Disagreement(
            row=reference[keys[i]],
            forecasts={model: tuple(float(p) for p in forecasts[model][i]) for model in models},
            largest_distance=float(largest[i]),
        )
        for i in order
    ]


def main(log: Path | None = None) -> int:
    """Print the comparison of the saved log. Returns the process exit code."""
    log = log or log_path()
    if not log.is_file():
        print(
            f"Prediction log not found: {log}\nRun: python -m app.evaluation.backtesting",
            file=sys.stderr,
        )
        return 1
    rows = read_log(log)
    differences = paired_differences(rows)
    print(
        f"Paired differences on {differences[0].matches} matches (first minus second, 95% interval)"
    )
    print(
        "Brier score and log loss: negative means the first model is better; accuracy: positive.\n"
    )
    for difference in differences:
        verdict = difference.better or "no real difference"
        print(
            f"  {difference.first:20s} vs {difference.second:20s} {difference.measure:12s} "
            f"{difference.mean:+.4f}  [{difference.lower:+.4f}, {difference.upper:+.4f}]  "
            f"better: {verdict}"
        )
    for title, comparisons in (
        ("By season", by_season(rows)),
        ("By actual result", by_outcome(rows)),
        ("By matchup type (point-in-time K-Means groups, 0 = strongest)", by_matchup_type(rows)),
        (
            f"By home group v away group (at least {MIN_GROUP_PAIR_MATCHES} matches)",
            by_group_pair(rows),
        ),
    ):
        _print_breakdown(title, comparisons)
    print("\nAgreement between the models")
    for agreement in agreements(rows):
        print(
            f"  {agreement.first:20s} vs {agreement.second:20s} same prediction "
            f"{agreement.same_prediction:6.1%}   mean distance {agreement.mean_distance:.4f}"
        )
    print(f"  all three predict the same outcome in {all_agree(rows):.1%} of the matches")
    print("\nLargest disagreements (home / draw / away)")
    for disagreement in largest_disagreements(rows):
        match = disagreement.row
        forecasts = "; ".join(
            f"{model} {' / '.join(f'{p:.2f}' for p in probabilities)}"
            for model, probabilities in disagreement.forecasts.items()
        )
        print(
            f"  {match.match_date} {match.home_team} {match.home_goals}-{match.away_goals} "
            f"{match.away_team} (distance {disagreement.largest_distance:.2f}): {forecasts}"
        )
    return 0


def _print_breakdown(title: str, comparisons: Sequence[SubsetComparison]) -> None:
    print(f"\n{title}: Brier score per model (lower is better)")
    header = "".join(f"{model:>21s}" for model in (*COMPARED_MODELS, REFERENCE_MODEL))
    print(f"  {'subset':28s} {'matches':>7s}{header}   best (real lead?)")
    for comparison in comparisons:
        values = "".join(
            f"{comparison.brier[model].value:21.4f}"
            for model in (*COMPARED_MODELS, REFERENCE_MODEL)
        )
        real = "yes" if comparison.lead is not None and comparison.lead.significant else "no"
        print(
            f"  {comparison.label:28s} {comparison.matches:7d}{values}   {comparison.best} ({real})"
        )


def _forecasts(
    rows: Sequence[PredictionLogRow], models: Sequence[str]
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Each model's n x 3 forecasts and predicted outcome codes, in the same match order."""
    by_model = _rows_by_model(rows)
    forecasts, predictions = {}, {}
    for model in models:
        if model not in by_model:
            raise ValueError(f"model {model!r} is not in the log")
        ordered = [by_model[model][key] for key in sorted(by_model[model])]
        forecasts[model] = np.array([[r.p_home, r.p_draw, r.p_away] for r in ordered])
        predictions[model] = np.array([r.predicted for r in ordered])
    return forecasts, predictions


def _rows_by_model(rows: Sequence[PredictionLogRow]) -> dict[str, dict[tuple, PredictionLogRow]]:
    by_model: dict[str, dict[tuple, PredictionLogRow]] = {}
    for row in rows:
        by_model.setdefault(row.model, {})[(row.match_date, row.home_team, row.away_team)] = row
    if not by_model:
        raise ValueError("the prediction log is empty")
    keys = sorted(next(iter(by_model.values())))
    if any(sorted(model_rows) != keys for model_rows in by_model.values()):
        raise ValueError("models cover different matches; they cannot be compared match by match")
    return by_model


if __name__ == "__main__":
    sys.exit(main())
