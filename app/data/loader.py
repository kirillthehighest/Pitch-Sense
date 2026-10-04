"""Reading raw Football-Data.co.uk season files from disk."""

from pathlib import Path

import pandas as pd

from app.data.models import Match
from app.data.preprocessing import DataValidationError, matches_from_frame, sort_chronologically


def read_raw_season(path: Path) -> pd.DataFrame:
    """Read one season file as stored: every cell as text, empty cells as ``""``.

    ``utf-8-sig`` also accepts files that start with a byte-order mark (2024-25 onwards). Blank
    lines are kept so that reported line numbers match the file.
    """
    return pd.read_csv(
        path, encoding="utf-8-sig", dtype=str, keep_default_na=False, skip_blank_lines=False
    )


def load_season(path: Path) -> list[Match]:
    """Load and validate one season file named after its season, such as ``2006-07.csv``."""
    matches = matches_from_frame(read_raw_season(path), season=path.stem, source=path.name)
    return sort_chronologically(matches)


def load_competition(folder: Path) -> list[Match]:
    """Load every season file of one competition folder as a single chronological list."""
    paths = sorted(folder.glob("*.csv"))
    if not paths:
        raise DataValidationError(f"no season files (*.csv) in {folder}")
    matches = [match for path in paths for match in load_season(path)]
    competitions = sorted({match.competition for match in matches})
    if len(competitions) > 1:
        raise DataValidationError(
            f"{folder.name}: files mix competitions {', '.join(competitions)}"
        )
    return sort_chronologically(matches)
