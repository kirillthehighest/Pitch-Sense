"""Shared fixtures: small synthetic seasons in the Football-Data.co.uk file format, and the
services and Qt application that the GUI and end-to-end tests run on (off-screen)."""

import csv
import os
from collections.abc import Callable
from itertools import permutations
from pathlib import Path

import pandas as pd
import pytest

from app.data.build_database import build_database
from app.data.competitions import Competition
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


FOUR_TEAM_LEAGUE = {"SP1": Competition("SP1", "La Liga", teams=4)}


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

    def make(
        database: Path,
        competitions: tuple[str, ...] = ("SP1",),
        closed_doors_season: str = CLOSED_DOORS_SEASON,
    ) -> AppContext:
        def open_league(code: str) -> LeagueServices:
            catalog = DataCatalog.load(database, competition=code)
            return LeagueServices(
                code=code,
                name=competition(code).name,
                catalog=catalog,
                predictions=PredictionService(catalog.matches, min_training_matches=3),
                teams=TeamService(catalog.matches),
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
            run_task=run_now,
            report_error=errors.append,
        )

    return make


@pytest.fixture
def app_context(make_app_context, database: Path):
    """The services of the fixture database: one league, SP1, with two 4-team seasons."""
    return make_app_context(database)
