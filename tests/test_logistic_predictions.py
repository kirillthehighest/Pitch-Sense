from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.data.models import Outcome
from app.prediction.logistic_features import build_features
from app.prediction.logistic_predictions import run_logistic_regression

SETTINGS = {"min_training_matches": 2}  # with the SP1 settings: L2 = 0.1


def test_weekly_refit_on_the_fixture_season(season_matches):
    # 1 Sept 2006 is a Friday. Features exist from day 2. Week of 1-3 Sept: no training data yet.
    # Week of 4-10 Sept: days 2-3 were both home wins, so it is not predicted. Week of 11-12 Sept:
    # trained on days 2-10, which contain all three results.
    predictions = run_logistic_regression(season_matches, **SETTINGS)

    assert [p.match.match_date.day for p in predictions] == [11, 12]
    assert [p.training_matches for p in predictions] == [9, 9]


def test_each_week_is_trained_only_on_matches_before_its_monday(
    season_matches, next_season_matches
):
    matches = [*season_matches, *next_season_matches]
    features = build_features(matches)

    predictions = run_logistic_regression(matches, **SETTINGS)

    assert len(predictions) == 14
    for prediction in predictions:
        day = prediction.match.match_date
        monday = day - timedelta(days=day.weekday())
        assert prediction.training_matches == sum(f.match.match_date < monday for f in features)


def test_probabilities_are_valid_and_training_converges(season_matches, next_season_matches):
    for prediction in run_logistic_regression([*season_matches, *next_season_matches], **SETTINGS):
        assert len(prediction.probabilities) == 3
        assert min(prediction.probabilities) >= 0
        assert sum(prediction.probabilities) == pytest.approx(1)
        assert prediction.training_converged
        assert prediction.training_iterations >= 1


def test_changing_a_result_never_changes_predictions_on_or_before_its_day(
    season_matches, next_season_matches
):
    target = next_season_matches[6]  # 7 September 2007
    changed = replace(target, home_goals=target.away_goals + 2, result=Outcome.HOME_WIN)
    changed_season = [*next_season_matches[:6], changed, *next_season_matches[7:]]

    original = run_logistic_regression([*season_matches, *next_season_matches], **SETTINGS)
    after_change = run_logistic_regression([*season_matches, *changed_season], **SETTINGS)

    def by_day(predictions):
        return {p.match.match_date: (p.features, p.probabilities) for p in predictions}

    original_days, changed_days = by_day(original), by_day(after_change)
    for day in range(1, 8):
        assert original_days[date(2007, 9, day)] == changed_days[date(2007, 9, day)]
    assert any(
        original_days[date(2007, 9, day)] != changed_days[date(2007, 9, day)]
        for day in range(8, 13)
    )


def test_minimum_training_size_must_be_positive(season_matches):
    with pytest.raises(ValueError, match="min_training_matches"):
        run_logistic_regression(season_matches, min_training_matches=0)
