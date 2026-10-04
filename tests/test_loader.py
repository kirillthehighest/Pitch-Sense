from datetime import date

import pytest

from app.data.loader import load_competition, load_season
from app.data.preprocessing import DataValidationError


def test_load_season_reads_columns_by_name_and_accepts_a_byte_order_mark(
    tmp_path, raw_season_rows, write_season_file
):
    reordered_with_odds = [
        {"B365H": "1.50", "B365D": "4.00", **dict(reversed(row.items()))} for row in raw_season_rows
    ]
    path = write_season_file(
        tmp_path / "SP1" / "2006-07.csv", reordered_with_odds, byte_order_mark=True
    )

    matches = load_season(path)

    assert len(matches) == 12
    assert {match.season for match in matches} == {"2006-07"}
    assert {match.competition for match in matches} == {"SP1"}
    assert matches[0].match_date == date(2006, 9, 1)
    assert matches[0].home_team == "Alpha"


def test_load_season_returns_matches_in_chronological_order(
    tmp_path, raw_season_rows, write_season_file
):
    path = write_season_file(tmp_path / "2006-07.csv", list(reversed(raw_season_rows)))

    dates = [match.match_date for match in load_season(path)]

    assert dates == sorted(dates)


def test_load_season_rejects_a_file_not_named_after_a_season(
    tmp_path, raw_season_rows, write_season_file
):
    path = write_season_file(tmp_path / "laliga.csv", raw_season_rows)

    with pytest.raises(DataValidationError, match="season label"):
        load_season(path)


def test_load_competition_joins_seasons_chronologically(
    tmp_path, raw_season_rows, next_season_rows, write_season_file
):
    folder = tmp_path / "SP1"
    write_season_file(folder / "2007-08.csv", next_season_rows)
    write_season_file(folder / "2006-07.csv", raw_season_rows)

    matches = load_competition(folder)

    assert len(matches) == 24
    assert [match.season for match in matches] == ["2006-07"] * 12 + ["2007-08"] * 12
    assert [match.match_date for match in matches] == sorted(match.match_date for match in matches)


def test_load_competition_rejects_an_empty_folder(tmp_path):
    with pytest.raises(DataValidationError, match="no season files"):
        load_competition(tmp_path)


def test_load_competition_rejects_mixed_competitions(
    tmp_path, raw_season_rows, next_season_rows, write_season_file
):
    other_league = [{**row, "Div": "E0"} for row in next_season_rows]
    write_season_file(tmp_path / "2006-07.csv", raw_season_rows)
    write_season_file(tmp_path / "2007-08.csv", other_league)

    with pytest.raises(DataValidationError, match="mix competitions"):
        load_competition(tmp_path)
