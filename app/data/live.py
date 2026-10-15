"""The season in progress (Phase 18): its results so far and the matches still to be played.

Two public sources are downloaded only when the user asks (the "Actualizează datele" button, or
``python -m app.data.update``) and stored unchanged in ``LIVE_DIR``:

- Football-Data.co.uk, the source of the past seasons, gives the results of the season so far
  (``<code>.csv``, in the format of ``data/raw``);
- openfootball (public domain, CC0) gives the calendar of the whole season (``<code>.json``). It is
  used only for the matches not played yet, because its scores arrive later than Football-Data's.

The two sources name the teams differently ("Club Atlético de Madrid", "Ath Madrid"). The names
are matched from the data itself: a match played in both, on the same day with the same score,
ties the two names together. A calendar team that cannot be matched with certainty is reported,
and its matches are left out rather than guessed.
"""

import hashlib
import json
import re
import shutil
import ssl
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from app import __version__
from app.data.competitions import COMPETITIONS, Competition
from app.data.loader import read_raw_season
from app.data.models import Fixture, Match
from app.data.paths import BUNDLED_LIVE_DIR, LIVE_DIR
from app.data.preprocessing import (
    DataValidationError,
    in_progress_season_problems,
    matches_from_frame,
    parse_season_label,
    season_date_window,
    season_of,
    sort_chronologically,
)

RESULTS_URL = "https://www.football-data.co.uk/mmz4281/{years}/{code}.csv"
CALENDAR_URL = (
    "https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{calendar}.json"
)
MANIFEST = "update.json"
MAX_DOWNLOAD_BYTES = 5_000_000  # a season file is about 0.2 MB
# Certificate bundles kept by the operating system (macOS first). Python from python.org has none
# of its own; Windows needs none, as Python reads its certificate store.
SYSTEM_CERTIFICATES = (
    "/etc/ssl/cert.pem",
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/pki/tls/certs/ca-bundle.crt",
)
MIN_NAME_VOTES = 2  # matches that must tie two team names together
NAME_AGREEMENT = 0.75  # share of a name's matches that must point to the same team
MAX_REPORTED_PROBLEMS = 20
_KICKOFF = re.compile(r"(\d{2}):(\d{2})")

Fetch = Callable[[str], bytes]


@dataclass(frozen=True, slots=True)
class CalendarMatch:
    """One match of the openfootball calendar, with its score when the calendar has it."""

    match_date: date
    kickoff_time: time | None
    home_team: str
    away_team: str
    score: tuple[int, int] | None  # full time


@dataclass(frozen=True, eq=False)
class LiveLeague:
    """One league's season in progress, in Football-Data's team names."""

    competition: str
    season: str
    matches: tuple[Match, ...]  # played so far, in chronological order
    fixtures: tuple[Fixture, ...]  # still to be played, in chronological order
    unmatched_teams: tuple[str, ...]  # calendar names that could not be matched with certainty
    updated_at: datetime  # when the files were downloaded (UTC)


@dataclass(frozen=True, eq=False)
class UpdateSummary:
    """What one update downloaded."""

    season: str
    updated_at: datetime
    leagues: tuple[LiveLeague, ...]


def fetch(url: str, timeout: float = 30.0) -> bytes:
    """Download a file over HTTPS, checking the server against the system's certificates."""
    request = urllib.request.Request(url, headers={"User-Agent": f"PitchSense/{__version__}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_tls_context()) as response:
            data = response.read(MAX_DOWNLOAD_BYTES + 1)
    except urllib.error.HTTPError as error:
        error.close()  # the error holds the server's response
        if error.code == 404:  # in summer, before the new season's files are published
            raise FileNotFoundError(f"{url} is not published yet (HTTP 404)") from None
        raise
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise DataValidationError(f"{url}: larger than {MAX_DOWNLOAD_BYTES} bytes")
    return data


def _tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    if context.cert_store_stats()["x509_ca"] == 0:
        for bundle in SYSTEM_CERTIFICATES:
            if Path(bundle).is_file():
                context.load_verify_locations(cafile=bundle)
                break
    return context


def season_years(season: str) -> str:
    """Football-Data's folder of a season: "2026-27" -> "2627"."""
    start_year, end_year = parse_season_label(season)
    return f"{start_year % 100:02d}{end_year % 100:02d}"


def parse_calendar(data: bytes, season: str, source: str) -> list[CalendarMatch]:
    """Read an openfootball calendar (JSON with a list of ``matches``) of one season."""
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DataValidationError(f"{source}: not a calendar: {error}") from None
    rows = document.get("matches") if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise DataValidationError(f"{source}: the calendar has no list of matches")
    first_day, last_day = season_date_window(season)
    calendar: list[CalendarMatch] = []
    problems: list[str] = []
    for number, row in enumerate(rows, start=1):
        try:
            entry = _calendar_entry(row)
        except (KeyError, TypeError, ValueError) as error:
            problems.append(f"match {number}: {error}")
            continue
        if not first_day <= entry.match_date <= last_day:
            problems.append(f"match {number}: date {entry.match_date} is outside season {season}")
            continue
        calendar.append(entry)
    pairs = Counter((entry.home_team, entry.away_team) for entry in calendar)
    problems.extend(
        f"{home} hosts {away} {count} times" for (home, away), count in pairs.items() if count > 1
    )
    if problems:
        raise DataValidationError(_report(source, problems))
    return calendar


def _calendar_entry(row: object) -> CalendarMatch:
    if not isinstance(row, Mapping):
        raise TypeError("a match must be an object")
    home_team, away_team = row["team1"], row["team2"]
    if not (isinstance(home_team, str) and home_team and isinstance(away_team, str) and away_team):
        raise ValueError("both team names are needed")
    if home_team == away_team:
        raise ValueError(f"a team cannot play itself: {home_team!r}")
    kickoff = None
    found = _KICKOFF.match(str(row.get("time") or ""))
    if found:
        kickoff = time(int(found.group(1)), int(found.group(2)))
    score = None
    # A score is {"ht": [...], "ft": [...]}, or only the full-time list (often for 0-0).
    full_time = row.get("score")
    if isinstance(full_time, Mapping):
        full_time = full_time.get("ft")
    if full_time is not None:
        if not (
            isinstance(full_time, list)
            and len(full_time) == 2
            and all(isinstance(goals, int) and goals >= 0 for goals in full_time)
        ):
            raise ValueError(f"a full-time score must be two goal counts, got {full_time!r}")
        score = (full_time[0], full_time[1])
    return CalendarMatch(date.fromisoformat(row["date"]), kickoff, home_team, away_team, score)


def match_team_names(
    calendar: Sequence[CalendarMatch], matches: Sequence[Match]
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Tie each calendar team name to a Football-Data name, from the matches both have played.

    A calendar match with a score is paired with the Football-Data match of the same day and the
    same score (or the day before or after, when the sources disagree on the date) when exactly
    one such match exists; each pairing is a vote for two pairs of names. A calendar name takes
    the Football-Data name with at least ``MIN_NAME_VOTES`` votes and ``NAME_AGREEMENT`` of its
    votes, and no two calendar names may take the same one. Returns the names and the calendar
    names left unmatched, sorted.
    """
    by_day_and_score: dict[tuple[date, int, int], list[Match]] = defaultdict(list)
    for match in matches:
        by_day_and_score[(match.match_date, match.home_goals, match.away_goals)].append(match)
    votes: dict[str, Counter[str]] = defaultdict(Counter)
    for entry in calendar:
        if entry.score is None:
            continue
        candidates = by_day_and_score.get((entry.match_date, *entry.score), [])
        if not candidates:
            candidates = [
                match
                for shift in (-1, 1)
                for match in by_day_and_score.get(
                    (entry.match_date + timedelta(days=shift), *entry.score), []
                )
            ]
        if len(candidates) == 1:
            votes[entry.home_team][candidates[0].home_team] += 1
            votes[entry.away_team][candidates[0].away_team] += 1
    chosen = {}
    for name, counter in votes.items():
        best, count = counter.most_common(1)[0]
        if count >= MIN_NAME_VOTES and count >= NAME_AGREEMENT * counter.total():
            chosen[name] = best
    taken = Counter(chosen.values())
    names = {name: team for name, team in chosen.items() if taken[team] == 1}
    calendar_names = {name for entry in calendar for name in (entry.home_team, entry.away_team)}
    return names, tuple(sorted(calendar_names - names.keys()))


def build_live_league(
    code: str,
    season: str,
    matches: Sequence[Match],
    calendar: Sequence[CalendarMatch],
    updated_at: datetime,
) -> LiveLeague:
    """Join the results and the calendar of one league: the fixtures are the calendar matches
    that neither source reports as played, in Football-Data's team names."""
    names, unmatched = match_team_names(calendar, matches)
    played = {(match.home_team, match.away_team) for match in matches}
    fixtures = []
    for entry in calendar:
        home_team, away_team = names.get(entry.home_team), names.get(entry.away_team)
        if entry.score is not None or home_team is None or away_team is None:
            continue  # played (the results will come from Football-Data), or a name not matched
        if (home_team, away_team) not in played:
            fixtures.append(
                Fixture(code, season, entry.match_date, home_team, away_team, entry.kickoff_time)
            )
    fixtures.sort(key=lambda f: (f.match_date, f.kickoff_time or time.min, f.home_team))
    return LiveLeague(
        competition=code,
        season=season,
        matches=tuple(sort_chronologically(matches)),
        fixtures=tuple(fixtures),
        unmatched_teams=unmatched,
        updated_at=updated_at,
    )


def read_manifest(folder: Path) -> dict | None:
    """The description of the files in ``folder``, or None when nothing was downloaded there."""
    path = folder / MANIFEST
    if not path.is_file():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        parse_season_label(manifest["season"])
        datetime.fromisoformat(manifest["updated_at"])
        if not isinstance(manifest["leagues"], list):
            raise TypeError("leagues must be a list")
    except (ValueError, KeyError, TypeError) as error:
        raise DataValidationError(f"{path}: not a valid update description: {error}") from None
    return manifest


def load_live_league(
    code: str, folder: Path = LIVE_DIR, competitions: Mapping[str, Competition] = COMPETITIONS
) -> LiveLeague | None:
    """One league's season in progress from ``folder``; None when it was never downloaded.

    Raises DataValidationError when the files are damaged or the results cannot be a season in
    progress of the league.
    """
    manifest = read_manifest(folder)
    if manifest is None or code not in manifest["leagues"]:
        return None
    season = manifest["season"]
    source = f"{code} {season}"
    matches = matches_from_frame(read_raw_season(folder / f"{code}.csv"), season, source)
    if any(match.competition != code for match in matches):
        raise DataValidationError(f"{source}: the results are not {code} matches")
    problems = in_progress_season_problems(matches, competitions[code].teams_in(season))
    if problems:
        raise DataValidationError(_report(source, problems))
    calendar = parse_calendar((folder / f"{code}.json").read_bytes(), season, f"{source} calendar")
    updated_at = datetime.fromisoformat(manifest["updated_at"])
    return build_live_league(code, season, matches, calendar, updated_at)


def update_live_data(
    target: Path = LIVE_DIR,
    codes: Sequence[str] = tuple(COMPETITIONS),
    *,
    today: date | None = None,
    fetch: Fetch = fetch,
    competitions: Mapping[str, Competition] = COMPETITIONS,
) -> UpdateSummary:
    """Download the season in progress of every league, check it, and only then replace the files
    in ``target``: a failed download or a damaged file leaves the previous data as it was."""
    season = season_of(today or date.today())
    staging = target.with_name(target.name + ".download")
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    try:
        sources = {}
        for code in codes:
            calendar = competitions[code].calendar
            if not calendar:
                raise DataValidationError(f"{code}: no calendar source in COMPETITIONS")
            for name, url in (
                (f"{code}.csv", RESULTS_URL.format(years=season_years(season), code=code)),
                (f"{code}.json", CALENDAR_URL.format(season=season, calendar=calendar)),
            ):
                data = fetch(url)
                (staging / name).write_bytes(data)
                sources[name] = {"url": url, "sha256": hashlib.sha256(data).hexdigest()}
        updated_at = datetime.now(UTC).replace(microsecond=0)
        manifest = {
            "season": season,
            "updated_at": updated_at.isoformat(),
            "leagues": list(codes),
            "sources": sources,
            "application": __version__,
        }
        (staging / MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        leagues = tuple(load_live_league(code, staging, competitions) for code in codes)
        _replace_folder(staging, target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return UpdateSummary(season, updated_at, leagues)


def copy_bundled_live(source: Path = BUNDLED_LIVE_DIR, target: Path = LIVE_DIR) -> bool:
    """Put the snapshot shipped in a package into the user's folder when it is newer than what
    is there. Run from the source code both folders are the same. Returns whether it copied."""
    if source.resolve() == target.resolve():
        return False
    shipped = read_manifest(source) if source.is_dir() else None
    if shipped is None:
        return False
    try:
        present = read_manifest(target) if target.is_dir() else None
    except DataValidationError:
        present = None  # a damaged folder is replaced
    if present is not None and present["updated_at"] >= shipped["updated_at"]:
        return False
    staging = target.with_name(target.name + ".download")
    shutil.rmtree(staging, ignore_errors=True)
    shutil.copytree(source, staging)
    try:
        _replace_folder(staging, target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return True


def _replace_folder(new: Path, target: Path) -> None:
    old = target.with_name(target.name + ".old")
    shutil.rmtree(old, ignore_errors=True)
    if target.exists():
        target.rename(old)
    new.rename(target)
    shutil.rmtree(old, ignore_errors=True)


def _report(source: str, problems: list[str]) -> str:
    shown = problems[:MAX_REPORTED_PROBLEMS]
    more = len(problems) - len(shown)
    lines = [f"{source}: {len(problems)} problem(s)", *(f"  {problem}" for problem in shown)]
    if more:
        lines.append(f"  ... and {more} more")
    return "\n".join(lines)
