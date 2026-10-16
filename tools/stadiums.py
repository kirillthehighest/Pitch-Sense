"""Collect the clubs' stadium photos from Wikipedia: ``python tools/stadiums.py``.

The team asked for photos of stadiums to make the club and match pages livelier (Phase 22), and
allowed protected images in this private project. For every club whose crest was found
(``app/assets/crests/sources.json`` names its Wikipedia article), the ground of the article's
infobox is read and the stadium article's lead image is saved ``WIDTH`` pixels wide as
``app/assets/stadiums/<stadium>.jpg``; clubs sharing a ground share the photo.
``sources.json`` lists every club's stadium, its article and the image file. A stadium without a
photo, or with a lead image that is not a photo of it (a map, a logo), leaves its clubs without
one: they keep the league's colour.

The photos belong to their authors (their licences are on their Wikimedia pages). They are used
only in this private university project and are not published. Run it again only to refresh them;
look at every result before committing it (``--sheet`` draws all of them on one page).

The tool uses Qt for the images: install it with ``python -m pip install -e ".[tools]"``.
"""

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # run as a script

from app.services.images import CRESTS_DIR, STADIUMS_DIR, crest_slug  # noqa: E402
from tools.crests import api, download  # noqa: E402

WIDTH = 1024  # pixels: sharp in the right half of a club's head on a high-density screen
# The ground of a club's infobox, its first link: "| ground = [[Old Trafford]]" or
# "| stadium = [[Camp Nou]]"
GROUND = re.compile(
    r"^\s*\|\s*(?:ground|stadium)\s*=[^\n\[]*\[\[([^|\]\n#]+)", re.MULTILINE | re.IGNORECASE
)
# Images that are not photos of a stadium: drawings, and files named as logos, maps or plans
# (as whole words: "Mapei Stadium" is a photo)
NOT_A_PHOTO = re.compile(
    r"\.(svg|gif)$|(?<![a-z])(logo|map|location|plan|crest|badge|kit|seating)(?![a-z])",
    re.IGNORECASE,
)
# The photo of a stadium article's infobox, when the article has no lead image
INFOBOX_IMAGE = re.compile(
    r"^\s*\|\s*image\s*=\s*(?:\[\[)?(?:File:|Image:)?([^|\]\n<{}]+)", re.MULTILINE | re.IGNORECASE
)
JPEG_QUALITY = 75
# Clubs whose article links another place first; checked by hand on the sheet.
GROUNDS = {"Chievo": "Stadio Marcantonio Bentegodi"}


def article_title(url: str) -> str:
    return urllib.parse.unquote(url.rsplit("/wiki/", 1)[1]).replace("_", " ")


def lead_wikitext(article: str) -> str:
    """The wikitext of an article's lead (with its infobox); empty when there is no such page."""
    answer = api(action="parse", page=article, prop="wikitext", section="0", redirects="1")
    return answer["parse"]["wikitext"] if "parse" in answer else ""


def ground_of(article: str) -> str | None:
    """The stadium named in the club article's infobox, or None."""
    found = GROUND.search(lead_wikitext(article))
    return found.group(1).strip() if found else None


def stadium_photos(stadiums: list[str]) -> dict[str, tuple[str, str]]:
    """Each stadium article's lead image: its file name and a WIDTH-wide copy (50 at once)."""
    photos = {}
    for start in range(0, len(stadiums), 50):
        chunk = stadiums[start : start + 50]
        answer = api(
            action="query",
            prop="pageimages",
            titles="|".join(chunk),
            pilicense="any",
            piprop="thumbnail|name",
            pithumbsize=str(WIDTH),
            pilimit="50",
            redirects="1",
        )["query"]
        renamed = {item["from"]: item["to"] for item in answer.get("redirects", [])}
        pages = {page["title"]: page for page in answer["pages"]}
        for stadium in chunk:
            page = pages.get(renamed.get(stadium, stadium), {})
            if "pageimage" in page and "thumbnail" in page:
                photos[stadium] = (page["pageimage"], page["thumbnail"]["source"])
    return photos


def infobox_photo(stadium: str) -> tuple[str, str] | None:
    """The image of the stadium article's infobox: its file name and a WIDTH-wide copy."""
    found = INFOBOX_IMAGE.search(lead_wikitext(stadium))
    if found is None:
        return None
    name = found.group(1).strip()
    page = api(
        action="query", titles=f"File:{name}", prop="imageinfo", iiprop="url", iiurlwidth=str(WIDTH)
    )["query"]["pages"][0]
    if "imageinfo" not in page:
        return None
    return name.replace(" ", "_"), page["imageinfo"][0]["thumburl"]


def save_jpeg(data: bytes, path: Path) -> None:
    """Save a photo at most WIDTH pixels wide as a JPEG of JPEG_QUALITY (Wikimedia's copies come
    up to 1280 pixels wide, some as PNG panoramas): about 150 KB a photo."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication, QImage

    QGuiApplication.instance() or QGuiApplication([])
    image = QImage.fromData(data)
    if image.isNull():
        raise ValueError(f"not an image: {path.name}")
    if image.width() > WIDTH:
        image = image.scaledToWidth(WIDTH, Qt.TransformationMode.SmoothTransformation)
    if not image.save(str(path), "JPG", JPEG_QUALITY):
        raise OSError(f"could not write {path}")


def photo_of(ground: str, lead: tuple[str, str] | None) -> tuple[str, str] | None:
    """The stadium's photo: its infobox image (the lead image can be the stadium's logo), else
    the article's lead image; None when neither is a photo."""
    for found in (infobox_photo(ground), lead):
        if found is not None and not NOT_A_PHOTO.search(found[0]):
            return found
    return None


def collect(only: set[str] | None = None) -> None:
    """Collect every club's stadium photo, or only those of ``only``, kept with the others."""
    STADIUMS_DIR.mkdir(parents=True, exist_ok=True)
    clubs = json.loads((CRESTS_DIR / "sources.json").read_text(encoding="utf-8"))
    path = STADIUMS_DIR / "sources.json"
    sources = []
    if only:
        unknown = only - {club["team"] for club in clubs}
        if unknown:
            raise SystemExit(f"unknown teams: {', '.join(sorted(unknown))}")
        clubs = [club for club in clubs if club["team"] in only]
        sources = [s for s in json.loads(path.read_text(encoding="utf-8")) if s["team"] not in only]
    grounds = {}
    for club in clubs:
        team, article = club["team"], article_title(club["article"])
        grounds[team] = GROUNDS.get(team) or ground_of(article)
        print(f"{team} ({club['competition']}): {article} -> {grounds[team]}", flush=True)
    stadiums = sorted({ground for ground in grounds.values() if ground})
    leads = stadium_photos(stadiums)
    photos = {ground: photo_of(ground, leads.get(ground)) for ground in stadiums}
    saved = {source["image"] for source in sources}
    for club in clubs:
        team, ground = club["team"], grounds[club["team"]]
        photo = photos.get(ground) if ground else None
        if photo is None:
            print(f"  no photo: {team}, ground {ground!r}")
            continue
        file_name, address = photo
        slug = crest_slug(ground)
        if slug not in saved:
            save_jpeg(download(address), STADIUMS_DIR / f"{slug}.jpg")
            saved.add(slug)
        sources.append(
            {
                "team": team,
                "competition": club["competition"],
                "stadium": ground,
                "image": slug,
                "article": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(ground)}",
                "file": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(file_name)}",
            }
        )
    sources.sort(key=lambda source: source["team"])
    path.write_text(json.dumps(sources, indent=1, ensure_ascii=False) + "\n", "utf-8")
    used = {source["image"] for source in sources}
    for unused in STADIUMS_DIR.glob("*.jpg"):  # a photo no club uses any more
        if unused.stem not in used:
            unused.unlink()
    print(f"{len(sources)} clubs, {len(used)} stadium photos in {STADIUMS_DIR}")


def contact_sheet(target: Path) -> None:
    """Every stadium photo with its clubs, four to a row, to look at them before committing."""
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

    QGuiApplication.instance() or QGuiApplication([])
    sources = json.loads((STADIUMS_DIR / "sources.json").read_text(encoding="utf-8"))
    clubs: dict[str, list[str]] = {}
    for source in sources:
        clubs.setdefault(source["image"], []).append(source["team"])
    columns, width, height = 6, 320, 230
    rows = (len(clubs) + columns - 1) // columns
    sheet = QImage(columns * width, rows * height, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#16161A"))
    painter = QPainter(sheet)
    painter.setPen(QColor("#F5F5F7"))
    for index, (image, teams) in enumerate(sorted(clubs.items())):
        x, y = index % columns * width, index // columns * height
        photo = QImage(str(STADIUMS_DIR / f"{image}.jpg"))
        scaled = photo.scaled(width - 16, 170, Qt.AspectRatioMode.KeepAspectRatio)
        painter.drawImage(x + (width - scaled.width()) // 2, y + 8, scaled)
        painter.drawText(
            QRect(x + 4, y + 182, width - 8, 44),
            Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
            ", ".join(teams),
        )
    painter.end()
    sheet.save(str(target))
    print(f"{target}: {len(clubs)} stadiums")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sheet", type=Path, help="draw every photo into this PNG file instead")
    parser.add_argument("--only", nargs="+", metavar="TEAM", help="collect only these teams")
    arguments = parser.parse_args()
    if arguments.sheet:
        contact_sheet(arguments.sheet)
    else:
        collect(set(arguments.only) if arguments.only else None)
