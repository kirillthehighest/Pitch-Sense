import math
from dataclasses import replace
from datetime import date

import pytest

from app.data.build_database import build_database
from app.data.models import Match, Outcome
from app.evaluation.logistic_calibration import calibrate, constant_frequency_log_loss, main

SEASONS = {"warm_up_seasons": ("2006-07",), "calibration_seasons": ("2007-08",)}


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


def test_constant_frequency_reference_hand_example():
    # Warm-up results H, H, D, A give frequencies 1/2, 1/4, 1/4: a home win costs -ln(1/2).
    matches = [
        make(date(2006, 9, 1), 1, 0, "2006-07"),
        make(date(2006, 9, 8), 2, 0, "2006-07"),
        make(date(2006, 9, 15), 1, 1, "2006-07"),
        make(date(2006, 9, 22), 0, 1, "2006-07"),
        make(date(2007, 9, 1), 3, 0, "2007-08"),
    ]

    assert constant_frequency_log_loss(matches, **SEASONS) == pytest.approx(math.log(2))


def test_results_are_sorted_best_first(season_matches, next_season_matches):
    results = calibrate(
        [*season_matches, *next_season_matches],
        l2_values=(0.01, 1.0, 10.0),
        min_training_matches=2,
        **SEASONS,
    )

    losses = [result.log_loss for result in results]
    assert len(results) == 3
    assert losses == sorted(losses)
    assert all(result.matches == 12 for result in results)


def test_seasons_outside_warm_up_and_calibration_are_never_read(
    season_matches, next_season_matches
):
    later = [
        replace(m, season="2008-09", match_date=m.match_date.replace(year=2008))
        for m in season_matches
    ]
    flipped_later = [
        replace(
            later_match,
            home_goals=later_match.away_goals,
            away_goals=later_match.home_goals,
            result=Outcome.from_score(later_match.away_goals, later_match.home_goals),
        )
        for later_match in later
    ]
    options = {"l2_values": (0.1,), "min_training_matches": 2, **SEASONS}

    without_later = calibrate([*season_matches, *next_season_matches], **options)
    with_later = calibrate([*season_matches, *next_season_matches, *later], **options)
    with_flipped = calibrate([*season_matches, *next_season_matches, *flipped_later], **options)

    assert without_later == with_later == with_flipped


def test_calibration_needs_predicted_calibration_matches(season_matches, next_season_matches):
    with pytest.raises(ValueError, match="too few training matches"):
        calibrate([*season_matches, *next_season_matches], min_training_matches=1000, **SEASONS)
    with pytest.raises(ValueError, match="calibration seasons"):
        calibrate(season_matches, **SEASONS)


def test_main_prints_the_best_value(raw_data_dir, tmp_path, capsys):
    database_path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, database_path, {"SP1": 4})

    exit_code = main(database_path, min_training_matches=2)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "(12 matches)" in output
    assert "Best: L2 = " in output


def test_main_explains_a_missing_database(tmp_path, capsys):
    assert main(tmp_path / "missing.db") == 1
    assert "python -m app.data.build_database" in capsys.readouterr().err
