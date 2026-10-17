from datetime import date

import pytest

from app.data.build_database import build_database
from app.data.models import Match, Outcome
from app.evaluation.elo_calibration import calibrate, constant_prediction_error, main


def make(day: date, home_goals: int, away_goals: int, season: str) -> Match:
    return Match(
        competition="SP1",
        season=season,
        match_date=day,
        home_team="A",
        away_team="B",
        home_goals=home_goals,
        away_goals=away_goals,
        result=Outcome.from_score(home_goals, away_goals),
    )


WARM_UP = make(date(2006, 9, 1), 1, 0, "2006-07")
CALIBRATION = make(date(2007, 9, 1), 1, 0, "2007-08")
LATER = make(date(2008, 9, 1), 0, 3, "2008-09")
SEASONS = {"warm_up_seasons": ("2006-07",), "calibration_seasons": ("2007-08",)}


def test_hand_computed_error_of_one_calibration_match():
    (result,) = calibrate(
        [WARM_UP, CALIBRATION],
        k_factors=(20,),
        home_advantages=(0,),
        goal_margins=(False,),
        **SEASONS,
    )

    # After the warm-up match A has 1510 and B 1490: E = 1 / (1 + 10^(-20/400)) = 0.528750.
    assert (result.k_factor, result.home_advantage, result.matches) == (20, 0, 1)
    assert result.mean_squared_error == pytest.approx((1 - 0.528750) ** 2, abs=1e-6)


def test_the_goal_margin_is_one_more_choice_of_the_grid():
    wide_warm_up = make(date(2006, 9, 1), 3, 0, "2006-07")

    results = calibrate(
        [wide_warm_up, CALIBRATION], k_factors=(20,), home_advantages=(0,), **SEASONS
    )

    # With the margin A gains 20 * 1.75 * 0.5 = 17.5 in the warm-up: E = 0.550199; else 0.528750.
    errors = {result.goal_margin: result.mean_squared_error for result in results}
    assert errors[True] == pytest.approx((1 - 0.550199) ** 2, abs=1e-6)
    assert errors[False] == pytest.approx((1 - 0.528750) ** 2, abs=1e-6)
    assert results[0].goal_margin is True  # the calibration home win was predicted better
    assert results[0].settings.goal_margin is True


def test_seasons_outside_warm_up_and_calibration_are_never_read():
    flipped_later = make(date(2008, 9, 1), 3, 0, "2008-09")

    without_later = calibrate([WARM_UP, CALIBRATION], **SEASONS)
    with_later = calibrate([WARM_UP, CALIBRATION, LATER], **SEASONS)
    with_flipped_later = calibrate([WARM_UP, CALIBRATION, flipped_later], **SEASONS)

    assert without_later == with_later == with_flipped_later


def test_results_are_sorted_best_first(season_matches, next_season_matches):
    results = calibrate(
        [*season_matches, *next_season_matches],
        k_factors=(10, 40),
        home_advantages=(0, 100),
        **SEASONS,
    )

    errors = [result.mean_squared_error for result in results]
    assert len(results) == 8  # 2 K x 2 H x with and without the goal margin
    assert errors == sorted(errors)
    assert all(result.matches == 12 for result in results)


def test_calibration_needs_calibration_matches():
    with pytest.raises(ValueError, match="calibration seasons"):
        calibrate([WARM_UP], **SEASONS)


def test_constant_prediction_error_uses_the_warm_up_average():
    warm_up_loss = make(date(2006, 9, 8), 0, 2, "2006-07")

    # The warm-up average home score is (1 + 0) / 2 = 0.5; the calibration home win scores 1.
    assert constant_prediction_error([WARM_UP, warm_up_loss, CALIBRATION], **SEASONS) == 0.25


def test_main_prints_the_best_pair(raw_data_dir, tmp_path, capsys, four_team_league):
    database_path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, database_path, four_team_league)

    exit_code = main(database_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "(12 matches)" in output
    assert "Best: K = " in output


def test_main_explains_a_missing_database(tmp_path, capsys):
    exit_code = main(tmp_path / "missing.db")

    assert exit_code == 1
    assert "python -m app.data.build_database" in capsys.readouterr().err
