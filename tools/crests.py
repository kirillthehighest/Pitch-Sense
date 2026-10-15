"""Collect the clubs' crests from Wikipedia: ``python tools/crests.py``.

For every team in the database and in the season in progress, the club's English Wikipedia article
is found (by the calendar's full club name when the team plays this season, otherwise by its
Football-Data name and country), and the article's lead image, the crest of its infobox, is saved
at most ``SIZE`` pixels wide and high as ``app/ui/assets/crests/<team>.png``. ``sources.json``
lists the article and the image file of every crest; teams without a certain crest keep the
initials badge drawn by the application.

Crests are trademarks of their clubs. They are used here at low resolution only to identify the
teams in a private university project, and are not published. Run it again only to refresh them;
every result must be looked at before it is committed (``--sheet`` draws all of them on one page).
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # run as a script

from app import __version__  # noqa: E402
from app.data.competitions import COMPETITIONS  # noqa: E402
from app.data.live import fetch, load_live_league, match_team_names, parse_calendar  # noqa: E402
from app.data.paths import DATABASE_PATH, LIVE_DIR  # noqa: E402
from app.data.repository import MatchRepository  # noqa: E402
from app.ui.brand import CRESTS_DIR, crest_slug  # noqa: E402

SIZE = 128  # pixels: a low resolution, enough for the largest badge on screen
API = "https://en.wikipedia.org/w/api.php"
# Wikimedia asks every program to name itself and how to reach its authors.
USER_AGENT = (
    f"PitchSense/{__version__} (https://github.com/kirillthehighest/Pitch-Sense; "
    "university course project)"
)
PAUSE = 1.0  # seconds between requests
COUNTRIES = {"E0": "England", "SP1": "Spain", "I1": "Italy", "D1": "Germany", "F1": "France"}
# Football-Data names whose search finds no club, or another one; checked by hand on the sheet.
ARTICLES = {
    "Benevento": "Benevento Calcio",
    "Cadiz": "Cádiz CF",
    "Hamburg": "Hamburger SV",
    "Hercules": "Hércules CF",
    "Las Palmas": "UD Las Palmas",
    "Sociedad": "Real Sociedad",
    "Sp Gijon": "Sporting de Gijón",
    "St Pauli": "FC St. Pauli",
}
REJECTED = ("season", "women", "list of", "reserves", " ii", " b ", "under-", "academy")
# The crest of an article's infobox, when the article has no lead image the API can give.
INFOBOX_IMAGE = re.compile(
    r"^\s*\|\s*(?:image|logo|crest)\s*=\s*(?:\[\[)?(?:File:|Image:)?([^|\]\n<{}]+)",
    re.MULTILINE | re.IGNORECASE,
)


def download(url: str) -> bytes:
    """Fetch politely: one request a second, waiting and trying again when asked to slow down."""
    for attempt in range(5):
        time.sleep(PAUSE * (1 + 10 * attempt))
        try:
            return fetch(url, user_agent=USER_AGENT)
        except urllib.error.HTTPError as error:
            if error.code != 429:
                raise
    raise OSError(f"{url}: the server keeps asking to slow down")


def api(**parameters: str) -> dict:
    parameters.update(format="json", formatversion="2")
    return json.loads(download(f"{API}?{urllib.parse.urlencode(parameters)}"))


def teams_and_queries() -> dict[str, tuple[str, str]]:
    """Every team with its league and the text to search for."""
    found: dict[str, tuple[str, str]] = {}
    with MatchRepository.open(DATABASE_PATH) as repository:
        for code in COMPETITIONS:
            for team in repository.teams(code):
                found[team] = (code, f"{team} football club {COUNTRIES[code]}")
    for code in COMPETITIONS:
        league = load_live_league(code, LIVE_DIR)
        if league is None:
            continue
        calendar = parse_calendar((LIVE_DIR / f"{code}.json").read_bytes(), league.season, code)
        names, _ = match_team_names(calendar, league.matches)
        for full_name, team in names.items():
            found[team] = (code, full_name)
    return found


def club_article(query: str) -> str | None:
    """The first search result described as a football club, or None."""
    hits = api(action="query", list="search", srsearch=query, srlimit="5")["query"]["search"]
    titles = [hit["title"] for hit in hits]
    if not titles:
        return None
    pages = api(action="query", prop="description", titles="|".join(titles), redirects="1")
    described = {page["title"]: page.get("description", "") for page in pages["query"]["pages"]}
    for title in titles:
        text = f" {title.lower()} {described.get(title, '').lower()} "
        if "football" in text and "club" in text and not any(word in text for word in REJECTED):
            return title
    return None


def lead_images(articles: list[str]) -> dict[str, tuple[str, str]]:
    """Each article's lead image: its file name and the address of a small copy (50 at once)."""
    images = {}
    for start in range(0, len(articles), 50):
        answer = api(
            action="query",
            prop="pageimages",
            titles="|".join(articles[start : start + 50]),
            pilicense="any",
            piprop="thumbnail|name",
            pithumbsize=str(SIZE),
            pilimit="50",
            redirects="1",
        )["query"]
        # A title that redirects is answered under the article's own title.
        renamed = {item["from"]: item["to"] for item in answer.get("redirects", [])}
        pages = {page["title"]: page for page in answer["pages"]}
        for article in articles[start : start + 50]:
            page = pages.get(renamed.get(article, article), {})
            if "pageimage" in page and "thumbnail" in page:
                images[article] = (page["pageimage"], page["thumbnail"]["source"])
    return images


def infobox_image(article: str) -> tuple[str, str] | None:
    """The image named in the article's infobox: its file name and a small copy's address."""
    wikitext = api(action="parse", page=article, prop="wikitext", section="0", redirects="1")
    found = INFOBOX_IMAGE.search(wikitext["parse"]["wikitext"])
    if found is None:
        return None
    name = found.group(1).strip()
    page = api(
        action="query",
        titles=f"File:{name}",
        prop="imageinfo",
        iiprop="url",
        iiurlwidth=str(SIZE),
    )["query"]["pages"][0]
    if "imageinfo" not in page:
        return None
    return name.replace(" ", "_"), page["imageinfo"][0]["thumburl"]


def save_small(data: bytes, path: Path) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication, QImage

    QGuiApplication.instance() or QGuiApplication([])
    image = QImage.fromData(data)
    if image.isNull():
        raise ValueError(f"not an image: {path.name}")
    if max(image.width(), image.height()) > SIZE:
        image = image.scaled(
            SIZE,
            SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    if not image.save(str(path), "PNG"):
        raise OSError(f"could not write {path}")


def collect(only: set[str] | None = None) -> None:
    """Collect every team's crest, or only those of ``only``, kept with the others."""
    CRESTS_DIR.mkdir(parents=True, exist_ok=True)
    teams = sorted(teams_and_queries().items())
    sources_path = CRESTS_DIR / "sources.json"
    kept = []
    if only:
        unknown = only - {team for team, _ in teams}
        if unknown:
            raise SystemExit(f"unknown teams: {', '.join(sorted(unknown))}")
        teams = [(team, value) for team, value in teams if team in only]
        kept = [
            source
            for source in json.loads(sources_path.read_text(encoding="utf-8"))
            if source["team"] not in only
        ]
    articles = {}
    for team, (code, query) in teams:
        articles[team] = ARTICLES.get(team) or club_article(query)
        print(f"{team} ({code}): {query!r} -> {articles[team]}", flush=True)
    images = lead_images(sorted({article for article in articles.values() if article}))
    sources = kept
    for team, (code, query) in teams:
        article = articles[team]
        image = images.get(article) if article else None
        if image is None and article:
            image = infobox_image(article)
        if image is None:
            print(f"  no crest: {team} ({code}), searched {query!r}, article {article!r}")
            continue
        file_name, address = image
        save_small(download(address), CRESTS_DIR / f"{crest_slug(team)}.png")
        sources.append(
            {
                "team": team,
                "competition": code,
                "article": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(article)}",
                "file": f"https://en.wikipedia.org/wiki/File:{urllib.parse.quote(file_name)}",
            }
        )
        print(f"{team} ({code}): {article} -> {file_name}")
    sources.sort(key=lambda source: source["team"])
    sources_path.write_text(json.dumps(sources, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(f"{len(sources)} crests in {CRESTS_DIR}")


def contact_sheet(target: Path) -> None:
    """Every crest with its team name, ten to a row, to look at them before committing."""
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

    QGuiApplication.instance() or QGuiApplication([])
    sources = json.loads((CRESTS_DIR / "sources.json").read_text(encoding="utf-8"))
    columns, cell = 10, 150
    rows = (len(sources) + columns - 1) // columns
    sheet = QImage(columns * cell, rows * cell, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#1C2541"))
    painter = QPainter(sheet)
    painter.setPen(QColor("#F2F4F8"))
    for index, source in enumerate(sources):
        x, y = index % columns * cell, index // columns * cell
        crest = QImage(str(CRESTS_DIR / f"{crest_slug(source['team'])}.png"))
        scaled = crest.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio)
        painter.drawImage(x + (cell - scaled.width()) // 2, y + 8, scaled)
        painter.drawText(
            QRect(x, y + 110, cell, 36),
            Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
            f"{source['team']} ({source['competition']})",
        )
    painter.end()
    sheet.save(str(target))
    print(f"{target}: {len(sources)} crests")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sheet", type=Path, help="draw every crest into this PNG file instead")
    parser.add_argument("--only", nargs="+", metavar="TEAM", help="collect only these teams")
    arguments = parser.parse_args()
    if arguments.sheet:
        contact_sheet(arguments.sheet)
    else:
        collect(set(arguments.only) if arguments.only else None)
