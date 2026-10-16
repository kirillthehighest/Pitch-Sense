"""Where the images of the interface are: club crests and league images (Phase 19) and stadium
photos (Phase 22), shared by the window and by the local server of the web interface. All stay in
the private repository and the packages only; their sources are in each folder's
``sources.json``."""

import json
import re
from functools import cache
from pathlib import Path

from app.data.paths import ASSETS_DIR

CRESTS_DIR = ASSETS_DIR / "crests"  # <crest_slug(team)>.png, at most 128 pixels
LEAGUE_PHOTOS_DIR = ASSETS_DIR / "leagues"  # <code>.jpg, supplied by the team, see sources.json
STADIUMS_DIR = ASSETS_DIR / "stadiums"  # <stadium slug>.jpg from Wikipedia (tools/stadiums.py)
DEFAULT_TOP = 0.1  # where the banner's strip of an image starts, as a share of its height


def crest_slug(team: str) -> str:
    """The file name of a team's crest: "Nott'm Forest" -> "nott-m-forest"."""
    return re.sub(r"[^a-z0-9]+", "-", team.lower()).strip("-")


def crest_path(team: str) -> Path | None:
    """The file of the club's crest, or None when there is none for the team."""
    path = CRESTS_DIR / f"{crest_slug(team)}.png"
    return path if path.is_file() else None


def league_photo_path(code: str) -> Path | None:
    """The file of the league's image, or None."""
    path = LEAGUE_PHOTOS_DIR / f"{code}.jpg"
    return path if path.is_file() else None


@cache
def _photo_sources() -> dict[str, dict]:
    path = LEAGUE_PHOTOS_DIR / "sources.json"
    if not path.is_file():
        return {}
    return {entry["competition"]: entry for entry in json.loads(path.read_text(encoding="utf-8"))}


def photo_credit(code: str) -> str | None:
    """Where the league's image comes from, as the banner shows it."""
    entry = _photo_sources().get(code)
    return f"Imagine: {entry['source']}" if entry else None


def photo_top(code: str) -> float:
    """Where the banner's strip of the league's image starts, as a share of the image's height:
    just above the highest head, so no window width cuts the faces."""
    entry = _photo_sources().get(code)
    return float(entry.get("top", DEFAULT_TOP)) if entry else DEFAULT_TOP


@cache
def _stadium_sources() -> dict[str, dict]:
    path = STADIUMS_DIR / "sources.json"
    if not path.is_file():
        return {}
    return {entry["team"]: entry for entry in json.loads(path.read_text(encoding="utf-8"))}


def stadium_teams() -> list[str]:
    """The clubs with a stadium photo, in order."""
    return sorted(_stadium_sources())


def stadium_path(team: str) -> Path | None:
    """The photo of the club's stadium, or None when there is none."""
    entry = _stadium_sources().get(team)
    if entry is None:
        return None
    path = STADIUMS_DIR / f"{entry['image']}.jpg"
    return path if path.is_file() else None


def stadium_name(team: str) -> str | None:
    """The name of the club's stadium, when its photo is known, without the article's
    disambiguation: "Waldstadion (Frankfurt)" -> "Waldstadion"."""
    entry = _stadium_sources().get(team)
    return re.sub(r"\s*\([^)]*\)$", "", entry["stadium"]) if entry else None
