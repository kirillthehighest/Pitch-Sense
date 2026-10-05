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


@pytest.fixture
def database(raw_data_dir: Path, tmp_path: Path) -> Path:
    """A database built from the two fixture seasons, with 4 teams per season."""
    path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, path, {"SP1": 4})
    return path


@pytest.fixture(scope="session")
def application():
    """The Qt application of the GUI tests. Qt is imported here so other tests never load it."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def errors() -> list[str]:
    """Collects the error messages the screens report."""
    return []


@pytest.fixture
def app_context(application, database: Path, tmp_path: Path, errors: list[str]):
    """The services over the fixture database, with tasks run at once and errors collected.

    The backtest evaluates 2007-08 and the models start after 3 earlier matches, so that both
    small seasons are useful.
    """
    from app.services.catalog import DataCatalog
    from app.services.evaluation import EvaluationService
    from app.services.predictions import PredictionService
    from app.services.teams import TeamService
    from app.ui.context import AppContext
    from app.ui.worker import run_now

    catalog = DataCatalog.load(database)
    return AppContext(
        catalog=catalog,
        predictions=PredictionService(catalog.matches, min_training_matches=3),
        teams=TeamService(catalog.matches),
        evaluation=EvaluationService(
            tmp_path / "results" / "log.csv",
            database,
            first_evaluation_season="2007-08",
            min_training_matches=3,
        ),
        run_task=run_now,
        report_error=errors.append,
    )
