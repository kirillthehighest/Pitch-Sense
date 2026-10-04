"""SQLite storage for Match records."""

import sqlite3
from collections.abc import Iterable
from datetime import date, time
from pathlib import Path
from typing import Self

from app.data.models import Match, MatchStatistics, Outcome
from app.data.preprocessing import STATISTICS_COLUMNS, sort_chronologically

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    id                    INTEGER PRIMARY KEY,
    competition           TEXT    NOT NULL,
    season                TEXT    NOT NULL,
    match_date            TEXT    NOT NULL,  -- ISO 8601, YYYY-MM-DD
    kickoff_time          TEXT,              -- HH:MM, NULL when unknown
    home_team             TEXT    NOT NULL,
    away_team             TEXT    NOT NULL,
    home_goals            INTEGER NOT NULL CHECK (home_goals >= 0),
    away_goals            INTEGER NOT NULL CHECK (away_goals >= 0),
    result                TEXT    NOT NULL CHECK (result IN ('H', 'D', 'A')),
    -- Post-match statistics: all NULL when the source has none for the match.
    home_shots            INTEGER,
    away_shots            INTEGER,
    home_shots_on_target  INTEGER,
    away_shots_on_target  INTEGER,
    home_fouls            INTEGER,
    away_fouls            INTEGER,
    home_corners          INTEGER,
    away_corners          INTEGER,
    home_yellow_cards     INTEGER,
    away_yellow_cards     INTEGER,
    home_red_cards        INTEGER,
    away_red_cards        INTEGER,
    UNIQUE (competition, match_date, home_team, away_team)
);
CREATE INDEX IF NOT EXISTS matches_by_competition_and_season ON matches (competition, season);
"""

_STATISTICS_FIELDS = tuple(STATISTICS_COLUMNS.values())
_MATCH_COLUMNS = (
    "competition",
    "season",
    "match_date",
    "kickoff_time",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "result",
    *_STATISTICS_FIELDS,
)
_INSERT = (
    f"INSERT INTO matches ({', '.join(_MATCH_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in _MATCH_COLUMNS)})"
)
_SELECT = f"SELECT {', '.join(_MATCH_COLUMNS)} FROM matches"


class MatchRepository:
    """Stores and queries Match records in an SQLite database."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        connection.row_factory = sqlite3.Row
        connection.executescript(SCHEMA)
        self._connection = connection

    @classmethod
    def open(cls, path: Path) -> Self:
        """Open the database file at ``path``, creating it and its table when missing."""
        return cls(sqlite3.connect(path))

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exception_info: object) -> None:
        self.close()

    def replace_competition(self, competition: str, matches: Iterable[Match]) -> int:
        """Replace every stored match of ``competition`` with ``matches`` in one transaction.

        Returns the number of matches stored. If anything fails, the previous data is kept.
        """
        matches = list(matches)
        other_competitions = sorted({match.competition for match in matches} - {competition})
        if other_competitions:
            raise ValueError(
                f"matches belong to {', '.join(other_competitions)}, not {competition}"
            )
        with self._connection:
            self._connection.execute("DELETE FROM matches WHERE competition = ?", (competition,))
            self._connection.executemany(_INSERT, [_to_row(match) for match in matches])
        return len(matches)

    def matches(self, competition: str, season: str | None = None) -> list[Match]:
        """Return the matches of a competition, optionally of one season, in chronological order."""
        query, parameters = f"{_SELECT} WHERE competition = ?", [competition]
        if season is not None:
            query += " AND season = ?"
            parameters.append(season)
        rows = self._connection.execute(query, parameters).fetchall()
        return sort_chronologically(_from_row(row) for row in rows)

    def competitions(self) -> list[str]:
        """Return the codes of the stored competitions, sorted."""
        rows = self._connection.execute(
            "SELECT DISTINCT competition FROM matches ORDER BY competition"
        )
        return [row["competition"] for row in rows]

    def seasons(self, competition: str) -> list[str]:
        """Return the season labels of a competition in chronological order."""
        rows = self._connection.execute(
            "SELECT DISTINCT season FROM matches WHERE competition = ? ORDER BY season",
            (competition,),
        )
        return [row["season"] for row in rows]

    def teams(self, competition: str, season: str | None = None) -> list[str]:
        """Return the teams that played in a competition, optionally in one season, sorted."""
        condition, parameters = "competition = ?", [competition]
        if season is not None:
            condition += " AND season = ?"
            parameters.append(season)
        rows = self._connection.execute(
            f"SELECT home_team AS team FROM matches WHERE {condition} "
            f"UNION SELECT away_team FROM matches WHERE {condition} ORDER BY team",
            parameters * 2,
        )
        return [row["team"] for row in rows]


def _to_row(match: Match) -> tuple[object, ...]:
    if match.statistics is None:
        statistics: tuple[int | None, ...] = (None,) * len(_STATISTICS_FIELDS)
    else:
        statistics = tuple(getattr(match.statistics, field) for field in _STATISTICS_FIELDS)
    return (
        match.competition,
        match.season,
        match.match_date.isoformat(),
        match.kickoff_time.isoformat(timespec="minutes") if match.kickoff_time else None,
        match.home_team,
        match.away_team,
        match.home_goals,
        match.away_goals,
        match.result.value,
        *statistics,
    )


def _from_row(row: sqlite3.Row) -> Match:
    statistics = None
    if row["home_shots"] is not None:
        statistics = MatchStatistics(**{field: row[field] for field in _STATISTICS_FIELDS})
    return Match(
        competition=row["competition"],
        season=row["season"],
        match_date=date.fromisoformat(row["match_date"]),
        home_team=row["home_team"],
        away_team=row["away_team"],
        home_goals=row["home_goals"],
        away_goals=row["away_goals"],
        result=Outcome(row["result"]),
        kickoff_time=time.fromisoformat(row["kickoff_time"]) if row["kickoff_time"] else None,
        statistics=statistics,
    )
