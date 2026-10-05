import pytest

from app.data.build_database import build_database
from app.evaluation import elo_calibration, logistic_calibration, poisson_calibration
from app.evaluation.league_calibration import calibrate_league, main
from app.prediction.settings import EloSettings


@pytest.fixture
def two_seasons(season_matches, next_season_matches):
    return [*season_matches, *next_season_matches]


def test_each_model_gets_its_own_best_value(two_seasons):
    result = calibrate_league(two_seasons, min_training_matches=3)

    elo = elo_calibration.calibrate(two_seasons)[0]
    assert result.competition == "SP1"
    assert result.elo == elo
    assert result.poisson == poisson_calibration.calibrate(two_seasons)[0]
    assert (
        result.logistic
        == logistic_calibration.calibrate(
            two_seasons, elo=EloSettings(elo.k_factor, elo.home_advantage), min_training_matches=3
        )[0]
    )
    assert set(result.edges) <= {"K", "H", "N", "m", "L2"}


def test_one_league_at_a_time(two_seasons, next_season_matches):
    from dataclasses import replace

    with pytest.raises(ValueError, match="one competition"):
        calibrate_league([*two_seasons, replace(next_season_matches[0], competition="E0")])


def test_main_prints_the_values_for_the_settings(raw_data_dir, tmp_path, capsys, four_team_league):
    database_path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, database_path, four_team_league)

    assert main(database_path, min_training_matches=3) == 0
    output = capsys.readouterr().out
    assert '"SP1": (' in output
    assert main(tmp_path / "missing.db") == 1
