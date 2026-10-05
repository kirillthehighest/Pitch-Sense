from collections import Counter

import pytest

from app.data.build_database import build_database, main
from app.data.competitions import Competition
from app.data.preprocessing import DataValidationError
from app.data.repository import MatchRepository


def stored_match_count(database_path) -> int:
    with MatchRepository.open(database_path) as repository:
        return len(repository.matches("SP1"))


def test_build_stores_every_season(raw_data_dir, tmp_path, four_team_league):
    database_path = tmp_path / "pitchsense.db"

    summary = build_database(raw_data_dir, database_path, four_team_league)

    assert summary == {"SP1": Counter({"2006-07": 12, "2007-08": 12})}
    with MatchRepository.open(database_path) as repository:
        assert repository.seasons("SP1") == ["2006-07", "2007-08"]
        assert len(repository.matches("SP1")) == 24
    assert not (tmp_path / "pitchsense.db.tmp").exists()


def test_rebuild_replaces_the_previous_database(raw_data_dir, tmp_path, four_team_league):
    database_path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, database_path, four_team_league)
    (raw_data_dir / "SP1" / "2007-08.csv").unlink()

    build_database(raw_data_dir, database_path, four_team_league)

    assert stored_match_count(database_path) == 12


def test_incomplete_season_fails_and_keeps_the_previous_database(
    raw_data_dir, tmp_path, next_season_rows, write_season_file, four_team_league
):
    database_path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, database_path, four_team_league)
    write_season_file(raw_data_dir / "SP1" / "2007-08.csv", next_season_rows[:-1])

    with pytest.raises(DataValidationError, match="SP1 2007-08: expected 12 matches, found 11"):
        build_database(raw_data_dir, database_path, four_team_league)

    assert stored_match_count(database_path) == 24
    assert not (tmp_path / "pitchsense.db.tmp").exists()


def test_a_season_stopped_early_is_accepted_when_declared(
    raw_data_dir, tmp_path, next_season_rows, write_season_file
):
    write_season_file(raw_data_dir / "SP1" / "2007-08.csv", next_season_rows[:-2])
    stopped = {"SP1": Competition("SP1", "La Liga", 4, stopped_early={"2007-08": 10})}

    summary = build_database(raw_data_dir, tmp_path / "pitchsense.db", stopped)

    assert summary["SP1"] == Counter({"2006-07": 12, "2007-08": 10})


def test_a_season_stopped_early_must_have_the_declared_matches(
    raw_data_dir, tmp_path, next_season_rows, write_season_file
):
    write_season_file(raw_data_dir / "SP1" / "2007-08.csv", next_season_rows[:-3])
    stopped = {"SP1": Competition("SP1", "La Liga", 4, stopped_early={"2007-08": 10})}

    with pytest.raises(DataValidationError, match="SP1 2007-08: expected 10 matches, found 9"):
        build_database(raw_data_dir, tmp_path / "pitchsense.db", stopped)


def test_the_number_of_teams_can_change_between_seasons(raw_data_dir, tmp_path):
    changed = {"SP1": Competition("SP1", "La Liga", 5, team_changes={"2006-07": 4, "2007-08": 4})}

    summary = build_database(raw_data_dir, tmp_path / "pitchsense.db", changed)

    assert summary["SP1"].total() == 24
    with pytest.raises(DataValidationError, match="expected 5 teams, found 4"):
        build_database(
            raw_data_dir,
            tmp_path / "other.db",
            {"SP1": Competition("SP1", "La Liga", 5, team_changes={"2006-07": 4})},
        )


def test_an_unknown_competition_is_rejected(raw_data_dir, tmp_path):
    with pytest.raises(DataValidationError, match="SP1: unknown competition"):
        build_database(raw_data_dir, tmp_path / "pitchsense.db", competitions={})


def test_folder_name_must_match_the_competition_code(raw_data_dir, tmp_path):
    (raw_data_dir / "SP1").rename(raw_data_dir / "E0")

    with pytest.raises(ValueError, match="belong to SP1, not E0"):
        build_database(
            raw_data_dir, tmp_path / "pitchsense.db", {"E0": Competition("E0", "Premier", 4)}
        )


def test_missing_raw_folder_is_reported(tmp_path, four_team_league):
    with pytest.raises(DataValidationError, match="raw data folder not found"):
        build_database(tmp_path / "missing", tmp_path / "pitchsense.db", four_team_league)


def test_main_prints_a_summary(raw_data_dir, tmp_path, capsys, four_team_league):
    exit_code = main(raw_data_dir, tmp_path / "pitchsense.db", four_team_league)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "SP1 (La Liga): 24 matches in 2 seasons" in output
    assert "2006-07: 12 matches, 4 teams, complete" in output


def test_main_reports_a_failed_build(raw_data_dir, tmp_path, capsys):
    exit_code = main(
        raw_data_dir, tmp_path / "pitchsense.db", {"SP1": Competition("SP1", "La Liga", 20)}
    )

    errors = capsys.readouterr().err
    assert exit_code == 1
    assert "Build failed" in errors
    assert "expected 20 teams, found 4" in errors
    assert not (tmp_path / "pitchsense.db").exists()
