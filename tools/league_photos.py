"""Download the leagues' banner photos from Wikimedia Commons: ``python tools/league_photos.py``.

Each league has one freely licensed photo of a stadium that stands for it, chosen by looking at
the candidates (``PHOTOS``). The photo is saved 1600 pixels wide as
``app/ui/assets/leagues/<code>.jpg``; ``sources.json`` keeps its title, author, licence and page,
which the application shows (the banner's corner and Analiză → Surse). Only CC BY, CC BY-SA, CC0
and public-domain files are accepted.
"""

import json
import re
import sys
import time
import urllib.parse
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # run as a script

from app import __version__  # noqa: E402
from app.data.live import fetch  # noqa: E402
from app.ui.brand import LEAGUE_PHOTOS_DIR  # noqa: E402

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    f"PitchSense/{__version__} (https://github.com/kirillthehighest/Pitch-Sense; "
    "university course project)"
)
WIDTH = 1600
PHOTOS = {
    "E0": ("File:Anfield panorama, March 2013.jpg", "Anfield, Liverpool"),
    "SP1": ("File:CampNouPanorama.jpg", "Camp Nou, Barcelona"),
    "I1": ("File:Stadio San Siro Milano panorama.jpg", "San Siro, Milano"),
    "D1": ("File:2012-02-26 Dortmund01 (6791756854).jpg", "Signal Iduna Park, Dortmund"),
    "F1": ("File:Parc des princes - Ligue 1.jpg", "Parc des Princes, Paris"),
}
FREE_LICENCES = re.compile(r"^(CC BY(-SA)? \d\.\d|CC0|Public domain)", re.IGNORECASE)


def plain(html: str) -> str:
    """The text of a metadata field, without its links."""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", html))).strip()


def photo(title: str) -> tuple[bytes, dict]:
    """The photo, 1600 pixels wide, and its author, licence and page."""
    parameters = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": str(WIDTH),
        "format": "json",
        "formatversion": "2",
    }
    page = json.loads(fetch(f"{API}?{urllib.parse.urlencode(parameters)}", user_agent=USER_AGENT))
    info = page["query"]["pages"][0]["imageinfo"][0]
    metadata = info["extmetadata"]
    licence = plain(metadata["LicenseShortName"]["value"])
    if not FREE_LICENCES.match(licence):
        raise SystemExit(f"{title}: licence {licence!r} is not free enough")
    time.sleep(1)
    data = fetch(info["thumburl"], user_agent=USER_AGENT)
    return data, {
        "author": plain(metadata.get("Artist", {}).get("value", "unknown")),
        "licence": licence,
        "licence_url": metadata.get("LicenseUrl", {}).get("value", ""),
        "page": info["descriptionurl"],
    }


def main() -> None:
    LEAGUE_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    sources = []
    for code, (title, subject) in PHOTOS.items():
        data, details = photo(title)
        (LEAGUE_PHOTOS_DIR / f"{code}.jpg").write_bytes(data)
        sources.append({"competition": code, "title": subject, "file": title, **details})
        print(f"{code}: {subject}, {details['author']}, {details['licence']} ({len(data)} bytes)")
        time.sleep(1)
    (LEAGUE_PHOTOS_DIR / "sources.json").write_text(
        json.dumps(sources, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
