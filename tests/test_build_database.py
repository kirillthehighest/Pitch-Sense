from collections import Counter

import pytest

from app.data.build_database import build_database, main
from app.data.preprocessing import DataValidationError
from app.data.repository import MatchRepository

FOUR_TEAMS = {"SP1": 4}


def stored_match_count(database_path) -> int:
    with MatchRepository.open(database_path) as repository:
        return len(repository.matches("SP1"))


def test_build_stores_every_season(raw_data_dir, tmp_path):
    database_path = tmp_path / "pitchsense.db"

    summary = build_database(raw_data_dir, database_path, FOUR_TEAMS)

    assert summary == {"SP1": Counter({"2006-07": 12, "2007-08": 12})}
    with MatchRepository.open(database_path) as repository:
        assert repository.seasons("SP1") == ["2006-07", "2007-08"]
        assert len(repository.matches("SP1")) == 24
    assert not (tmp_path / "pitchsense.db.tmp").exists()


def test_rebuild_replaces_the_previous_database(raw_data_dir, tmp_path):
    database_path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, database_path, FOUR_TEAMS)
    (raw_data_dir / "SP1" / "2007-08.csv").unlink()

    build_database(raw_data_dir, database_path, FOUR_TEAMS)

    assert stored_match_count(database_path) == 12


def test_incomplete_season_fails_and_keeps_the_previous_database(
    raw_data_dir, tmp_path, next_season_rows, write_season_file
):
    database_path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, database_path, FOUR_TEAMS)
    write_season_file(raw_data_dir / "SP1" / "2007-08.csv", next_season_rows[:-1])

    with pytest.raises(DataValidationError, match="SP1 2007-08: expected 12 matches, found 11"):
        build_database(raw_data_dir, database_path, FOUR_TEAMS)

    assert stored_match_count(database_path) == 24
    assert not (tmp_path / "pitchsense.db.tmp").exists()


def test_competition_without_expected_team_count_is_rejected(raw_data_dir, tmp_path):
    with pytest.raises(DataValidationError, match="expected number of teams is unknown"):
        build_database(raw_data_dir, tmp_path / "pitchsense.db", teams_per_season={})


def test_folder_name_must_match_the_competition_code(raw_data_dir, tmp_path):
    (raw_data_dir / "SP1").rename(raw_data_dir / "E0")

    with pytest.raises(ValueError, match="belong to SP1, not E0"):
        build_database(raw_data_dir, tmp_path / "pitchsense.db", {"E0": 4})


def test_missing_raw_folder_is_reported(tmp_path):
    with pytest.raises(DataValidationError, match="raw data folder not found"):
        build_database(tmp_path / "missing", tmp_path / "pitchsense.db", FOUR_TEAMS)


def test_main_prints_a_summary(raw_data_dir, tmp_path, capsys):
    exit_code = main(raw_data_dir, tmp_path / "pitchsense.db", FOUR_TEAMS)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "SP1: 24 matches in 2 seasons" in output
    assert "2006-07: 12 matches, complete" in output


def test_main_reports_a_failed_build(raw_data_dir, tmp_path, capsys):
    exit_code = main(raw_data_dir, tmp_path / "pitchsense.db", {"SP1": 20})

    errors = capsys.readouterr().err
    assert exit_code == 1
    assert "Build failed" in errors
    assert "expected 20 teams, found 4" in errors
    assert not (tmp_path / "pitchsense.db").exists()
