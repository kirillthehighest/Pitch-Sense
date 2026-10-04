from dataclasses import replace
from datetime import date

import pytest

from app.algorithms.elo import DrawModel, actual_score
from app.data.models import Outcome
from app.prediction.elo_predictions import elo_outcome_predictions, run_elo


def test_weekly_draw_model_on_the_fixture_season(season_matches):
    # 1 Sept 2006 is a Friday. Week of 1-3 Sept: no earlier matches. Week of 4-10 Sept: fitted
    # on days 1-3. Week of 11-12 Sept: fitted on days 1-10.
    predictions = elo_outcome_predictions(run_elo(season_matches), min_matches=3)

    assert [p.prediction.match.match_date.day for p in predictions] == list(range(4, 13))
    assert [p.draw_model_matches for p in predictions] == [3] * 7 + [10] * 2


def test_each_week_uses_a_draw_model_fitted_on_earlier_matches_only(season_matches):
    run = run_elo(season_matches)
    first_three = run.predictions[:3]
    draw_model = DrawModel.fit(
        [p.expected_home_score for p in first_three],
        [actual_score(p.match.home_goals, p.match.away_goals) for p in first_three],
    )

    predictions = elo_outcome_predictions(run, min_matches=3)

    first = predictions[0]
    assert first.probabilities == draw_model.outcome_probabilities(
        first.prediction.expected_home_score
    )


def test_probabilities_keep_the_elo_expected_score(season_matches, next_season_matches):
    run = run_elo([*season_matches, *next_season_matches])

    for prediction in elo_outcome_predictions(run, min_matches=3):
        home, draw, away = prediction.probabilities
        assert min(home, draw, away) >= 0
        assert home + draw + away == pytest.approx(1, abs=1e-12)
        assert home + draw / 2 == pytest.approx(prediction.prediction.expected_home_score)


def test_changing_a_result_never_changes_probabilities_on_or_before_its_day(season_matches):
    target = season_matches[6]  # 7 September 2006
    changed = replace(target, home_goals=target.away_goals + 2, result=Outcome.HOME_WIN)

    def by_day(matches):
        predictions = elo_outcome_predictions(run_elo(matches), min_matches=3)
        return {p.prediction.match.match_date: p.probabilities for p in predictions}

    original = by_day(season_matches)
    after_change = by_day([*season_matches[:6], changed, *season_matches[7:]])

    for day in range(4, 8):
        assert original[date(2006, 9, day)] == after_change[date(2006, 9, day)]
    assert any(
        original[date(2006, 9, day)] != after_change[date(2006, 9, day)] for day in range(8, 13)
    )


def test_too_few_earlier_matches_means_no_probabilities(season_matches):
    assert elo_outcome_predictions(run_elo(season_matches)) == []
    with pytest.raises(ValueError, match="min_matches"):
        elo_outcome_predictions(run_elo(season_matches), min_matches=0)
