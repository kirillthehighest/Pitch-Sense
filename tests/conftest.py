"""Shared fixtures: small synthetic seasons in the Football-Data.co.uk file format, and the
services and Qt application that the GUI and end-to-end tests run on (off-screen)."""

import csv
import io
import json
import os
import urllib.error
from collections.abc import Callable
from datetime import date
from itertools import permutations
from pathlib import Path

import pandas as pd
import pytest

from app.data.build_database import build_database
from app.data.competitions import Competition
from app.data.live import CALENDAR_URL, RESULTS_URL, update_live_data
from app.data.models import Match
from app.data.preprocessing import matches_from_frame

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # before Qt is first imported

STATISTICS_HEADER = ("HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR")
TEAMS = ("Alpha", "Bravo", "Charlie", "Delta")


@pytest.fixture
def raw_season_rows() -> list[dict[str, str]]:
    """A complete 4-team double round-robin for 2006-07 (12 matches), one per day from 1 Sept."""
    rows = []
    for number, (home_team, away_team) in enumerate(permutations(TEAMS, 2)):
        home_goals, away_goals = number % 3, (number + 1) % 2
        result = "H" if home_goals > away_goals else "A" if home_goals < away_goals else "D"
        rows.append(
            {
                "Div": "SP1",
                "Date": f"{number + 1:02d}/09/06",
                "HomeTeam": home_team,
                "AwayTeam": away_team,
                "FTHG": str(home_goals),
                "FTAG": str(away_goals),
                "FTR": result,
                **{column: str(number % 5) for column in STATISTICS_HEADER},
            }
        )
    return rows


@pytest.fixture
def write_season_file() -> Callable[..., Path]:
    """Return a function that writes raw rows to a CSV file, optionally with a byte-order mark."""

    def write(path: Path, rows: list[dict[str, str]], *, byte_order_mark: bool = False) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        encoding = "utf-8-sig" if byte_order_mark else "utf-8"
        with path.open("w", encoding=encoding, newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    return write


@pytest.fixture
def next_season_rows(raw_season_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """The same fixtures played one season later (2007-08)."""
    return [{**row, "Date": row["Date"].replace("/06", "/07")} for row in raw_season_rows]


@pytest.fixture
def raw_data_dir(
    tmp_path: Path,
    raw_season_rows: list[dict[str, str]],
    next_season_rows: list[dict[str, str]],
    write_season_file: Callable[..., Path],
) -> Path:
    """A raw data folder with one competition (SP1) and two complete 4-team seasons."""
    raw_dir = tmp_path / "raw"
    write_season_file(raw_dir / "SP1" / "2006-07.csv", raw_season_rows)
    write_season_file(raw_dir / "SP1" / "2007-08.csv", next_season_rows)
    return raw_dir


@pytest.fixture
def season_matches(raw_season_rows: list[dict[str, str]]) -> list[Match]:
    """The fixture season as validated Match records, in file order (one match per day)."""
    return matches_from_frame(pd.DataFrame(raw_season_rows, dtype=str), "2006-07", source="fixture")


@pytest.fixture
def next_season_matches(next_season_rows: list[dict[str, str]]) -> list[Match]:
    """The same fixtures one season later (2007-08) as validated Match records."""
    return matches_from_frame(
        pd.DataFrame(next_season_rows, dtype=str), "2007-08", source="fixture"
    )


FOUR_TEAM_LEAGUE = {"SP1": Competition("SP1", "La Liga", teams=4, calendar="es.1")}


@pytest.fixture
def four_team_league() -> dict[str, Competition]:
    """The competition registry of the fixture seasons: SP1 with 4 teams."""
    return dict(FOUR_TEAM_LEAGUE)


@pytest.fixture
def database(raw_data_dir: Path, tmp_path: Path, four_team_league) -> Path:
    """A database built from the two fixture seasons, with 4 teams per season."""
    path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, path, four_team_league)
    return path


@pytest.fixture
def two_league_database(raw_season_rows, next_season_rows, write_season_file, tmp_path):
    """La Liga (Alpha to Delta) and a Premier League of other teams, two seasons each."""
    renamed = {"Alpha": "Echo", "Bravo": "Foxtrot", "Charlie": "Golf", "Delta": "Hotel"}
    raw_dir = tmp_path / "raw_two_leagues"  # apart from raw_data_dir
    for name, rows in (("2006-07", raw_season_rows), ("2007-08", next_season_rows)):
        write_season_file(raw_dir / "SP1" / f"{name}.csv", rows)
        english = [
            {
                **row,
                "Div": "E0",
                "HomeTeam": renamed[row["HomeTeam"]],
                "AwayTeam": renamed[row["AwayTeam"]],
            }
            for row in rows
        ]
        write_season_file(raw_dir / "E0" / f"{name}.csv", english)
    path = tmp_path / "two_leagues.db"
    leagues = {**FOUR_TEAM_LEAGUE, "E0": Competition("E0", "Premier League", teams=4)}
    build_database(raw_dir, path, leagues)
    return path


# The season in progress of the fixture league: 2008-09, as the two public sources give it.
LIVE_SEASON = "2008-09"
LIVE_TODAY = date(2008, 9, 10)
LIVE_PLAYED = 7  # Football-Data's results so far: the first 7 matches, 1 to 7 September 2008
LIVE_SCORED = 6  # the calendar lags: it has the scores of the first 6 only
CALENDAR_NAMES = {
    "Alpha": "Alpha CF",
    "Bravo": "Bravo United",
    "Charlie": "Real Charlie",
    "Delta": "Delta FC",
}


@pytest.fixture
def live_files(raw_season_rows: list[dict[str, str]]) -> dict[str, bytes]:
    """The downloads of the season in progress: Football-Data's results so far (CSV) and the
    openfootball calendar of all 12 matches, with its own team names (JSON)."""
    played = [{**row, "Date": row["Date"].replace("/06", "/08")} for row in raw_season_rows]
    results = io.StringIO()
    writer = csv.DictWriter(results, fieldnames=list(played[0]))
    writer.writeheader()
    writer.writerows(played[:LIVE_PLAYED])
    calendar = {
        "name": "La Liga 2008/09",
        "matches": [
            {
                "round": f"Matchday {number + 1}",
                "date": f"2008-09-{number + 1:02d}",
                "time": "18:30",
                "team1": CALENDAR_NAMES[row["HomeTeam"]],
                "team2": CALENDAR_NAMES[row["AwayTeam"]],
                **(
                    {"score": {"ft": [int(row["FTHG"]), int(row["FTAG"])]}}
                    if number < LIVE_SCORED
                    else {}
                ),
            }
            for number, row in enumerate(played)
        ],
    }
    return {
        RESULTS_URL.format(years="0809", code="SP1"): results.getvalue().encode("utf-8"),
        CALENDAR_URL.format(season=LIVE_SEASON, calendar="es.1"): json.dumps(calendar).encode(),
    }


@pytest.fixture
def fake_fetch(live_files: dict[str, bytes]) -> Callable[[str], bytes]:
    """Serves the downloads of the season in progress; tests never use the network."""

    def fetch(url: str) -> bytes:
        if url not in live_files:
            raise urllib.error.URLError(f"no such file: {url}")
        return live_files[url]

    return fetch


@pytest.fixture
def live_dir(tmp_path: Path, fake_fetch, four_team_league) -> Path:
    """The season in progress of SP1, downloaded through ``fake_fetch``."""
    target = tmp_path / "live"
    update_live_data(
        target, ("SP1",), today=LIVE_TODAY, fetch=fake_fetch, competitions=four_team_league
    )
    return target


@pytest.fixture(scope="session")
def application():
    """The Qt application of the GUI tests, with the PitchSense theme. Qt is imported here so
    other tests never load it."""
    from PySide6.QtWidgets import QApplication

    from app.ui.theme import apply_theme

    application = QApplication.instance() or QApplication([])
    apply_theme(application)
    return application


@pytest.fixture
def errors() -> list[str]:
    """Collects the error messages the screens report."""
    return []


@pytest.fixture
def make_app_context(application, tmp_path: Path, errors: list[str]):
    """Return a function that opens the services of the given leagues of a database, with tasks
    run at once, errors collected and preferences and logs kept in the test folder.

    The backtests evaluate 2007-08 and the models start after 3 earlier matches, so that both
    small seasons are useful.
    """
    from app.data.competitions import competition
    from app.evaluation.leagues import CLOSED_DOORS_SEASON
    from app.services.catalog import DataCatalog
    from app.services.evaluation import EvaluationService
    from app.services.leagues import LeagueComparisonService
    from app.services.predictions import PredictionService
    from app.services.preferences import Preferences
    from app.services.teams import TeamService
    from app.ui.context import AppContext, LeagueServices
    from app.ui.worker import run_now

    results_dir = tmp_path / "results"

    def no_network() -> None:
        raise urllib.error.URLError("tests never use the network")

    def make(
        database: Path,
        competitions: tuple[str, ...] = ("SP1",),
        closed_doors_season: str = CLOSED_DOORS_SEASON,
        live_dir: Path | None = None,
        update_data: Callable[[], object] = no_network,
    ) -> AppContext:
        def open_league(code: str) -> LeagueServices:
            catalog = DataCatalog.load(database, competition=code, live_dir=live_dir)
            return LeagueServices(
                code=code,
                name=competition(code).name,
                catalog=catalog,
                predictions=PredictionService(
                    catalog.matches, catalog.fixtures, min_training_matches=3
                ),
                teams=TeamService(catalog.matches, in_progress=catalog.current_season),
                evaluation=EvaluationService(
                    results_dir / f"backtest_{code}.csv",
                    database,
                    competition=code,
                    first_evaluation_season="2007-08",
                    min_training_matches=3,
                ),
            )

        return AppContext(
            competitions=competitions,
            open_league=open_league,
            comparison=LeagueComparisonService(
                competitions,
                results_dir,
                database,
                first_evaluation_season="2007-08",
                min_training_matches=3,
                closed_doors_season=closed_doors_season,
            ),
            preferences=Preferences(tmp_path / "preferences.json"),
            update_data=update_data,
            run_task=run_now,
            report_error=errors.append,
        )

    return make


@pytest.fixture
def app_context(make_app_context, database: Path):
    """The services of the fixture database: one league, SP1, with two 4-team seasons."""
    return make_app_context(database)
