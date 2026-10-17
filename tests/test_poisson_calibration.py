import math
from datetime import date

import pytest

from app.data.build_database import build_database
from app.data.models import Match, Outcome
from app.evaluation.poisson_calibration import (
    RHO_VALUES,
    calibrate,
    half_lives,
    league_average_log_loss,
    main,
    team_windows,
)
from app.prediction.poisson_predictions import run_poisson


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


WARM_UP = make(date(2006, 9, 1), 1, 1, "2006-07")
CALIBRATION = make(date(2007, 9, 1), 1, 0, "2007-08")
SEASONS = {"warm_up_seasons": ("2006-07",), "calibration_seasons": ("2007-08",)}


def test_hand_computed_log_loss_of_one_calibration_match():
    (result,) = calibrate(
        [WARM_UP, CALIBRATION],
        windows=(19,),
        prior_matches=(1,),
        half_life_values=(None,),
        rho_values=(0.0,),
        **SEASONS,
    )

    # After a 1-1 the league averages are 1 and 1 and every strength is (1 + 1) / 2 / 1 = 1,
    # so both lambdas are 1 and P(1-0) = e^-1 * e^-1: the loss is -ln(e^-2) = 2.
    assert (result.team_window, result.prior_matches, result.matches) == (19, 1, 1)
    assert (result.half_life, result.rho) == (None, 0.0)
    assert result.mean_log_loss == pytest.approx(2.0, abs=1e-9)


def test_hand_computed_log_loss_with_the_dixon_coles_rho():
    results = calibrate(
        [WARM_UP, CALIBRATION],
        windows=(19,),
        prior_matches=(1,),
        half_life_values=(None,),
        rho_values=(0.0, -0.1),
        **SEASONS,
    )

    # tau(1, 0) = 1 + lambda_away * rho = 0.9: the 1-0 that happened was given 0.9 e^-2.
    losses = {result.rho: result.mean_log_loss for result in results}
    assert losses[-0.1] == pytest.approx(2.0 - math.log(0.9), abs=1e-9)
    assert results[0].rho == 0.0  # the correction made the 1-0 less likely


def test_each_rho_scores_as_the_corrected_model_predicts(season_matches, next_season_matches):
    matches = [*season_matches, *next_season_matches]
    rho = -0.12

    (result,) = calibrate(
        matches,
        windows=(6,),
        prior_matches=(2,),
        half_life_values=(3,),
        rho_values=(rho,),
        **SEASONS,
    )

    predictions = run_poisson(matches, result.settings(league_window=380))
    losses = [
        -math.log(p.distribution.probabilities[p.match.home_goals, p.match.away_goals])
        for p in predictions
        if p.match.season == "2007-08"
    ]
    assert result.mean_log_loss == pytest.approx(math.fsum(losses) / len(losses), abs=1e-12)


def test_reference_without_team_strengths():
    assert league_average_log_loss([WARM_UP, CALIBRATION], **SEASONS) == pytest.approx(2.0)


def test_seasons_outside_warm_up_and_calibration_are_never_read():
    later = make(date(2008, 9, 1), 0, 4, "2008-09")
    flipped_later = make(date(2008, 9, 1), 4, 0, "2008-09")

    without_later = calibrate([WARM_UP, CALIBRATION], **SEASONS)
    with_later = calibrate([WARM_UP, CALIBRATION, later], **SEASONS)
    with_flipped_later = calibrate([WARM_UP, CALIBRATION, flipped_later], **SEASONS)

    assert without_later == with_later == with_flipped_later


def test_results_are_sorted_best_first(season_matches, next_season_matches):
    results = calibrate(
        [*season_matches, *next_season_matches],
        windows=(1, 6),
        prior_matches=(1, 10),
        half_life_values=(None, 3),
        rho_values=(0.0, -0.1),
        **SEASONS,
    )

    losses = [result.mean_log_loss for result in results]
    assert len(results) == 16
    assert losses == sorted(losses)
    assert all(result.matches == 12 for result in results)


def test_calibration_needs_calibration_matches():
    with pytest.raises(ValueError, match="calibration seasons"):
        calibrate([WARM_UP], **SEASONS)


def test_main_prints_the_best_pair(raw_data_dir, tmp_path, capsys, four_team_league):
    database_path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, database_path, four_team_league)

    exit_code = main(database_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "(12 matches)" in output
    assert "Best: N = " in output


def test_main_explains_a_missing_database(tmp_path, capsys):
    assert main(tmp_path / "missing.db") == 1
    assert "python -m app.data.build_database" in capsys.readouterr().err


def test_the_team_window_grid_follows_the_league_size():
    assert team_windows(19) == (5, 10, 19, 38, 57, 76, 95)
    assert team_windows(17) == (5, 10, 17, 34, 51, 68, 85)


def test_the_half_life_grid_follows_the_league_size():
    assert half_lives(19) == (None, 5, 10, 19, 38, 76)
    assert half_lives(17) == (None, 4, 8, 17, 34, 68)
    assert RHO_VALUES[0] == 0 and RHO_VALUES[-1] == pytest.approx(-0.2) and len(RHO_VALUES) == 11
