"""Validation and normalization of raw Football-Data.co.uk rows into Match records."""

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import date, datetime, time, timedelta

import pandas as pd

from app.data.competitions import COMPETITIONS
from app.data.models import Match, MatchStatistics, Outcome

REQUIRED_COLUMNS = ("Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR")
TIME_COLUMN = "Time"
STATISTICS_COLUMNS = {
    "HS": "home_shots",
    "AS": "away_shots",
    "HST": "home_shots_on_target",
    "AST": "away_shots_on_target",
    "HF": "home_fouls",
    "AF": "away_fouls",
    "HC": "home_corners",
    "AC": "away_corners",
    "HY": "home_yellow_cards",
    "AY": "away_yellow_cards",
    "HR": "home_red_cards",
    "AR": "away_red_cards",
}
MAX_REPORTED_PROBLEMS = 20

_SEASON_LABEL = re.compile(r"(\d{4})-(\d{2})")
_FOUR_DIGIT_YEAR_DATE = re.compile(r"\d{2}/\d{2}/\d{4}")


class DataValidationError(ValueError):
    """Raised when raw match data breaks a validation rule."""


def parse_season_label(label: str) -> tuple[int, int]:
    """Return the start and end years of a season label such as ``"2006-07"``."""
    found = _SEASON_LABEL.fullmatch(label)
    if found is None:
        raise DataValidationError(f"season label must look like '2006-07', got {label!r}")
    start_year = int(found.group(1))
    if (start_year + 1) % 100 != int(found.group(2)):
        raise DataValidationError(f"season label years are not consecutive: {label!r}")
    return start_year, start_year + 1


def season_date_window(label: str) -> tuple[date, date]:
    """Return the earliest and latest dates a match of the season may have.

    The window runs from 1 July of the first year to 31 August of the second, which also covers
    seasons that finished late because of COVID-19: La Liga 2019/20 ended in July 2020 and Serie A
    2019/20 on 2 August 2020.
    """
    start_year, end_year = parse_season_label(label)
    return date(start_year, 7, 1), date(end_year, 8, 31)


def parse_match_date(text: str) -> date:
    """Parse a day-first date written as ``dd/mm/yy`` or ``dd/mm/yyyy`` (both occur in the data)."""
    date_format = "%d/%m/%Y" if _FOUR_DIGIT_YEAR_DATE.fullmatch(text) else "%d/%m/%y"
    try:
        return datetime.strptime(text, date_format).date()
    except ValueError:
        raise DataValidationError(f"date must be dd/mm/yy or dd/mm/yyyy, got {text!r}") from None


def parse_kickoff_time(text: str) -> time | None:
    """Parse an ``HH:MM`` kickoff time; an empty cell means the time is unknown."""
    if not text:
        return None
    try:
        return datetime.strptime(text, "%H:%M").time()
    except ValueError:
        raise DataValidationError(f"kickoff time must be HH:MM, got {text!r}") from None


def matches_from_frame(frame: pd.DataFrame, season: str, source: str) -> list[Match]:
    """Validate the rows of one raw season file and convert them into Match records.

    ``frame`` holds every cell as text, as returned by ``loader.read_raw_season``. Columns are
    selected by name and rows whose cells are all empty are skipped. Statistics are attached only
    when all 12 statistics columns exist. All invalid rows are reported together, by their line
    number in the file, in a single DataValidationError.
    """
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise DataValidationError(f"{source}: missing required columns: {', '.join(missing)}")
    first_day, last_day = season_date_window(season)
    has_time = TIME_COLUMN in frame.columns
    has_statistics = all(column in frame.columns for column in STATISTICS_COLUMNS)

    blank_rows = frame.eq("").all(axis="columns")
    matches: list[Match] = []
    problems: list[str] = []
    for position, (row, is_blank) in enumerate(
        zip(frame.to_dict("records"), blank_rows, strict=True)
    ):
        if is_blank:
            continue
        line = position + 2  # line 1 of the file is the header
        try:
            match = _match_from_row(row, season, has_time, has_statistics)
        except ValueError as error:
            problems.append(f"line {line}: {error}")
            continue
        if not first_day <= match.match_date <= last_day:
            problems.append(f"line {line}: date {match.match_date} is outside season {season}")
            continue
        matches.append(match)

    problems.extend(_duplicate_problems(matches))
    competitions = sorted({match.competition for match in matches})
    if len(competitions) > 1:
        problems.append(f"rows mix competitions: {', '.join(competitions)}")
    if problems:
        raise DataValidationError(_problem_report(source, problems))
    return matches


def season_structure_problems(
    matches: Iterable[Match], team_count: int, stopped_after: int | None = None
) -> list[str]:
    """List the ways a season departs from a double round-robin between ``team_count`` teams.

    In a double round-robin every team hosts every other team exactly once, so a 20-team season
    has 380 matches and 38 per team. A season officially stopped early (``stopped_after``
    matches) must have exactly that many matches and no team may exceed a full season. An empty
    list means the season is as expected.
    """
    if team_count < 2:
        raise ValueError(f"team_count must be at least 2, got {team_count}")
    matches = list(matches)
    problems = []

    seasons = sorted({match.season for match in matches})
    if len(seasons) > 1:
        problems.append(f"matches come from several seasons: {', '.join(seasons)}")
    appearances = Counter(team for match in matches for team in (match.home_team, match.away_team))
    if len(appearances) != team_count:
        problems.append(f"expected {team_count} teams, found {len(appearances)}")
    expected_matches = stopped_after or team_count * (team_count - 1)
    if len(matches) != expected_matches:
        problems.append(f"expected {expected_matches} matches, found {len(matches)}")
    expected_per_team = 2 * (team_count - 1)
    for team, played in sorted(appearances.items()):
        if played > expected_per_team or (stopped_after is None and played < expected_per_team):
            problems.append(f"{team} played {played} matches, expected {expected_per_team}")
    fixtures = Counter((match.home_team, match.away_team) for match in matches)
    for (home_team, away_team), hosted in sorted(fixtures.items()):
        if hosted > 1:
            problems.append(f"{home_team} hosted {away_team} {hosted} times")
    return problems


def in_progress_season_problems(matches: Iterable[Match], team_count: int) -> list[str]:
    """List the ways a season still being played departs from a double round-robin so far.

    No team may play more than a full season, no team may host another twice, and the season may
    not have more teams than the league. An empty list means the season can still be completed
    as a double round-robin between ``team_count`` teams.
    """
    if team_count < 2:
        raise ValueError(f"team_count must be at least 2, got {team_count}")
    matches = list(matches)
    problems = []
    seasons = sorted({match.season for match in matches})
    if len(seasons) > 1:
        problems.append(f"matches come from several seasons: {', '.join(seasons)}")
    appearances = Counter(team for match in matches for team in (match.home_team, match.away_team))
    if len(appearances) > team_count:
        problems.append(f"expected at most {team_count} teams, found {len(appearances)}")
    full_season = 2 * (team_count - 1)
    for team, played in sorted(appearances.items()):
        if played > full_season:
            problems.append(f"{team} played {played} matches, more than a season ({full_season})")
    fixtures = Counter((match.home_team, match.away_team) for match in matches)
    for (home_team, away_team), hosted in sorted(fixtures.items()):
        if hosted > 1:
            problems.append(f"{home_team} hosted {away_team} {hosted} times")
    return problems


def season_of(day: date) -> str:
    """The season a day belongs to; seasons start on 1 July: 2026-10-15 -> "2026-27"."""
    start_year = day.year if day.month >= 7 else day.year - 1
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def sort_chronologically(matches: Iterable[Match]) -> list[Match]:
    """Return the matches ordered by date, then kickoff time (unknown first), then home team."""
    return sorted(
        matches,
        key=lambda match: (match.match_date, match.kickoff_time or time.min, match.home_team),
    )


def local_kickoff(uk_time: time, hours_after_uk: int) -> time:
    """A kickoff Football-Data writes in UK time, in the league's own time (Phase 24). Before,
    the screens showed played matches an hour early in four of the five leagues. A kickoff that
    would move to the next day is refused: its date would be wrong too."""
    moved = datetime.combine(date.min, uk_time) + timedelta(hours=hours_after_uk)
    if moved.date() != date.min:
        raise DataValidationError(f"kickoff {uk_time:%H:%M} UK time is after midnight locally")
    return moved.time()


def _match_from_row(
    row: Mapping[str, str], season: str, has_time: bool, has_statistics: bool
) -> Match:
    result_code = row["FTR"].strip()
    try:
        result = Outcome(result_code)
    except ValueError:
        raise DataValidationError(f"FTR must be H, D or A, got {result_code!r}") from None
    return Match(
        competition=row["Div"].strip(),
        season=season,
        match_date=parse_match_date(row["Date"].strip()),
        home_team=row["HomeTeam"].strip(),
        away_team=row["AwayTeam"].strip(),
        home_goals=_parse_count(row["FTHG"], "FTHG"),
        away_goals=_parse_count(row["FTAG"], "FTAG"),
        result=result,
        kickoff_time=_local_kickoff_of(row) if has_time else None,
        statistics=_statistics_from_row(row) if has_statistics else None,
    )


def _local_kickoff_of(row: Mapping[str, str]) -> time | None:
    uk_time = parse_kickoff_time(row[TIME_COLUMN].strip())
    known = COMPETITIONS.get(row["Div"].strip())
    if uk_time is None or known is None:  # a league PitchSense does not know keeps the file's time
        return uk_time
    return local_kickoff(uk_time, known.hours_after_uk)


def _statistics_from_row(row: Mapping[str, str]) -> MatchStatistics | None:
    """Return the match statistics, or None when any of the 12 cells is empty."""
    cells = {column: row[column].strip() for column in STATISTICS_COLUMNS}
    if "" in cells.values():
        return None
    return MatchStatistics(
        **{
            field: _parse_count(cells[column], column)
            for column, field in STATISTICS_COLUMNS.items()
        }
    )


def _parse_count(text: str, column: str) -> int:
    """Parse a non-negative whole number such as goals, shots or cards."""
    text = text.strip()
    if not (text.isascii() and text.isdigit()):
        raise DataValidationError(f"{column} must be a non-negative whole number, got {text!r}")
    return int(text)


def _duplicate_problems(matches: Iterable[Match]) -> list[str]:
    counts = Counter((match.match_date, match.home_team, match.away_team) for match in matches)
    return [
        f"duplicate match: {home_team} vs {away_team} on {match_date} ({count} rows)"
        for (match_date, home_team, away_team), count in sorted(counts.items())
        if count > 1
    ]


def _problem_report(source: str, problems: list[str]) -> str:
    shown = problems[:MAX_REPORTED_PROBLEMS]
    lines = [f"{source}: {len(problems)} problem(s)", *shown]
    if len(problems) > len(shown):
        lines.append(f"... and {len(problems) - len(shown)} more")
    return "\n".join(lines)
