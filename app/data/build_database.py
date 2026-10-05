"""Rebuild the SQLite database from the raw season files.

Run from the project folder with ``python -m app.data.build_database``.

Every subfolder of ``data/raw`` holds one competition and is named by its code (for example
``SP1``; see ``app/data/competitions.py``). All its seasons are validated and must be complete
double round-robins (or, for a season officially stopped early, have exactly the matches played)
before anything is stored. The database is written to a temporary file first and replaces the
previous one only when the whole build succeeded.
"""

import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from app.data.competitions import COMPETITIONS, Competition
from app.data.loader import load_competition
from app.data.models import Match
from app.data.paths import DATABASE_PATH, RAW_DATA_DIR
from app.data.preprocessing import DataValidationError, season_structure_problems
from app.data.repository import MatchRepository


def build_database(
    raw_dir: Path,
    database_path: Path,
    competitions: Mapping[str, Competition] = COMPETITIONS,
) -> dict[str, Counter[str]]:
    """Validate every competition in ``raw_dir`` and store all of them in a fresh database.

    Returns the number of stored matches per competition and season.
    """
    if not raw_dir.is_dir():
        raise DataValidationError(f"raw data folder not found: {raw_dir}")
    folders = sorted(path for path in raw_dir.iterdir() if path.is_dir())
    if not folders:
        raise DataValidationError(f"no competition folders in {raw_dir}")

    temporary_path = database_path.with_name(f"{database_path.name}.tmp")
    temporary_path.unlink(missing_ok=True)
    summary = {}
    try:
        with MatchRepository.open(temporary_path) as repository:
            for folder in folders:
                matches = load_competition(folder)
                _check_seasons(folder.name, matches, competitions)
                repository.replace_competition(folder.name, matches)
                summary[folder.name] = Counter(match.season for match in matches)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    temporary_path.replace(database_path)
    return summary


def main(
    raw_dir: Path = RAW_DATA_DIR,
    database_path: Path = DATABASE_PATH,
    competitions: Mapping[str, Competition] = COMPETITIONS,
) -> int:
    """Build the database and print a summary per season. Returns the process exit code."""
    try:
        summary = build_database(raw_dir, database_path, competitions)
    except ValueError as error:
        print(f"Build failed:\n{error}", file=sys.stderr)
        return 1
    for code, seasons in summary.items():
        league = competitions[code]
        print(f"{code} ({league.name}): {seasons.total()} matches in {len(seasons)} seasons")
        for season, count in sorted(seasons.items()):
            state = "stopped early" if season in league.stopped_early else "complete"
            print(f"  {season}: {count} matches, {league.teams_in(season)} teams, {state}")
    print(f"Database written to {database_path}")
    return 0


def _check_seasons(
    code: str, matches: Sequence[Match], competitions: Mapping[str, Competition]
) -> None:
    if code not in competitions:
        raise DataValidationError(
            f"{code}: unknown competition; add it to COMPETITIONS in app/data/competitions.py"
        )
    league = competitions[code]
    by_season: dict[str, list[Match]] = {}
    for match in matches:
        by_season.setdefault(match.season, []).append(match)
    problems = [
        f"{code} {season}: {problem}"
        for season, season_matches in by_season.items()
        for problem in season_structure_problems(
            season_matches, league.teams_in(season), league.stopped_early.get(season)
        )
    ]
    if problems:
        raise DataValidationError("\n".join(problems))


if __name__ == "__main__":
    sys.exit(main())
