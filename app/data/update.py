"""Download the season in progress of every league.

Run from the project folder with ``python -m app.data.update`` (the window's "Actualizează
datele" button does the same). The results so far come from Football-Data.co.uk and the calendar
from openfootball; both are checked before they replace the files of the previous update, so a
failed download leaves the previous data as it was. See ``app/data/live.py``.
"""

import sys
from pathlib import Path

from app.data.live import update_live_data
from app.data.paths import LIVE_DIR
from app.data.preprocessing import DataValidationError


def main(target: Path = LIVE_DIR) -> int:
    """Download, check and store the season in progress. Returns the process exit code."""
    try:
        summary = update_live_data(target)
    except (DataValidationError, OSError) as error:
        print(f"Update failed, the previous data is kept:\n{error}", file=sys.stderr)
        return 1
    print(f"Season {summary.season}, downloaded {summary.updated_at:%Y-%m-%d %H:%M} UTC")
    for league in summary.leagues:
        line = (
            f"  {league.competition}: {len(league.matches)} matches played, "
            f"{len(league.fixtures)} to play"
        )
        if league.unmatched_teams:
            line += f"; not matched, their matches left out: {', '.join(league.unmatched_teams)}"
        print(line)
    print(f"Written to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
