"""The packaged application's self-test, run here on the synthetic seasons."""

import pytest

from app.data.build_database import build_database
from app.ui import self_test
from app.ui.self_test import run_self_test


@pytest.fixture
def three_seasons(raw_data_dir, next_season_rows, write_season_file, tmp_path, four_team_league):
    """The fixture seasons and a third one, 2008-09, so that the backtest log has two seasons
    and one of them can stand for the season played mostly without fans."""
    third = [{**row, "Date": row["Date"].replace("/07", "/08")} for row in next_season_rows]
    write_season_file(raw_data_dir / "SP1" / "2008-09.csv", third)
    path = tmp_path / "three_seasons.db"
    build_database(raw_data_dir, path, four_team_league)
    return path


def test_every_check_passes_on_working_data(make_app_context, three_seasons, capsys):
    app_context = make_app_context(three_seasons, closed_doors_season="2008-09")

    assert run_self_test(lambda: app_context) == 0

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 20
    assert all(line.startswith("ok") for line in lines)
    for check in (
        "typeface",
        "SVG icons",
        "calibration chart",
        "home advantage chart",
        "Ligi screen drawn",
    ):
        assert any(check in line for line in lines)
    # The missing logs were built by the test.
    assert app_context.league("SP1").evaluation.has_log
    assert app_context.comparison.missing() == []


def test_missing_data_fails_with_the_reason(application, capsys):
    def load():
        raise FileNotFoundError("Database not found")

    assert run_self_test(load) == 1
    assert capsys.readouterr().out == "FAILED  data: Database not found\n"


def test_without_a_console_the_report_goes_to_a_file(application, monkeypatch, tmp_path):
    def load():
        raise FileNotFoundError("Database not found")

    monkeypatch.setattr(self_test, "user_data_dir", lambda: tmp_path / "PitchSense")
    monkeypatch.setattr("sys.stdout", None)  # a packaged Windows application has no console

    assert self_test.run_self_test(load) == 1
    report = (tmp_path / "PitchSense" / "self-test.txt").read_text(encoding="utf-8")
    assert report == "FAILED  data: Database not found\n"
