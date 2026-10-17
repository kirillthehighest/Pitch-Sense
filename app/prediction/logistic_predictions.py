"""Run logistic regression through historical matches with a weekly, expanding-window refit.

At the start of every calendar week (Monday) a model is trained on all matches played before
that Monday, starting from the previous week's weights, and it predicts that week's matches.
No prediction ever uses a result from its own week, let alone its own day.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import groupby

import numpy as np

from app.algorithms.logistic_regression import fit
from app.data.models import Match, Outcome
from app.prediction.logistic_features import build_features
from app.prediction.poisson_predictions import PoissonPrediction
from app.prediction.schedule import week_start
from app.prediction.settings import LogisticSettings, settings_of

OUTCOME_ORDER = (Outcome.HOME_WIN, Outcome.DRAW, Outcome.AWAY_WIN)  # class index 0, 1, 2
MIN_TRAINING_MATCHES = 100


@dataclass(frozen=True, slots=True)
class LogisticPrediction:
    """The logistic regression view of one match."""

    match: Match
    features: tuple[float, ...]
    probabilities: tuple[float, float, float]  # home win, draw, away win
    training_matches: int
    training_iterations: int
    training_converged: bool


def run_logistic_regression(
    matches: Iterable[Match],
    settings: LogisticSettings | None = None,
    *,
    min_training_matches: int = MIN_TRAINING_MATCHES,
    poisson: Sequence[PoissonPrediction] | None = None,
) -> list[LogisticPrediction]:
    """Predict every match whose week starts with at least ``min_training_matches`` earlier ones.

    Training examples are the earlier matches' features (see ``build_features``) with their
    results; the features are standardized with each training set's own statistics. A week is
    predicted only when its training set contains all three results, because the model cannot
    learn a class it has never seen. Without ``settings`` the competition's calibrated L2, Elo,
    windows and features are used; ``poisson`` is passed on to ``build_features``.
    """
    if min_training_matches < 1:
        raise ValueError(f"min_training_matches must be at least 1, got {min_training_matches}")
    matches = list(matches)
    settings = settings or settings_of(matches).logistic
    training_rows: list[tuple[float, ...]] = []
    training_labels: list[int] = []
    weights = None
    predictions = []
    features = build_features(matches, settings, poisson=poisson)
    weeks = groupby(features, key=lambda f: week_start(f.match.match_date))
    for _, week in weeks:
        week_features = list(week)
        if len(training_rows) >= min_training_matches and len(set(training_labels)) == len(
            OUTCOME_ORDER
        ):
            model = fit(
                np.array(training_rows),
                training_labels,
                l2=settings.l2,
                initial_weights=weights,
            )
            weights = model.weights
            probabilities = model.predict_probabilities(
                np.array([features.values for features in week_features])
            )
            predictions.extend(
                LogisticPrediction(
                    match=features.match,
                    features=features.values,
                    probabilities=tuple(float(p) for p in row),
                    training_matches=len(training_rows),
                    training_iterations=model.iterations,
                    training_converged=model.converged,
                )
                for features, row in zip(week_features, probabilities, strict=True)
            )
        training_rows.extend(features.values for features in week_features)
        training_labels.extend(OUTCOME_ORDER.index(f.match.result) for f in week_features)
    return predictions
