"""What the application remembers between starts: the league on screen and "your team".

The choices are a small JSON file in the user's PitchSense folder (``PREFERENCES_PATH``). They
are a convenience: a missing file means "nothing chosen yet", a damaged one is ignored and
rewritten at the next choice, and a choice that cannot be saved (a read-only folder) lasts until
the application closes. A preferences file can never stop the application.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.data.paths import PREFERENCES_PATH


@dataclass(frozen=True, slots=True)
class FavouriteTeam:
    """The team the user follows, and the league it plays in."""

    competition: str
    team: str


class Preferences:
    """Reads the user's choices once and writes them back whenever one changes."""

    def __init__(self, path: Path = PREFERENCES_PATH) -> None:
        self.path = path
        self._values = self._read()

    @property
    def competition(self) -> str | None:
        """The league shown last time, if any."""
        value = self._values.get("competition")
        return value if isinstance(value, str) else None

    @property
    def favourite(self) -> FavouriteTeam | None:
        value = self._values.get("favourite")
        if isinstance(value, dict) and {"competition", "team"} <= value.keys():
            return FavouriteTeam(str(value["competition"]), str(value["team"]))
        return None

    def set_competition(self, code: str) -> bool:
        """Remember the league on screen; returns whether the choice was saved."""
        self._values["competition"] = code
        return self._write()

    def set_favourite(self, favourite: FavouriteTeam | None) -> bool:
        """Remember "your team" (None forgets it); returns whether the choice was saved."""
        if favourite is None:
            self._values.pop("favourite", None)
        else:
            self._values["favourite"] = {
                "competition": favourite.competition,
                "team": favourite.team,
            }
        return self._write()

    def _read(self) -> dict:
        try:
            values = json.loads(self.path.read_text(encoding="utf-8"))
        except OSError, ValueError:  # no file yet, or a damaged one: start from nothing
            return {}
        return values if isinstance(values, dict) else {}

    def _write(self) -> bool:
        """Save the choices; False when they could not be saved and live only in memory."""
        temporary = self.path.with_name(f"{self.path.name}.tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(self._values, indent=2), encoding="utf-8")
            temporary.replace(self.path)
        except OSError:
            return False
        return True
