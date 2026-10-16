"""The bookmakers' average odds of each match (Phase 23): a reference the models are measured
against, never an input to them (betting is out of the project's scope).

Football-Data.co.uk files give the market average of each outcome's decimal odds, collected
before kickoff: ``BbAvH``, ``BbAvD``, ``BbAvA`` (Betbrain) until 2018-19 and ``AvgH``, ``AvgD``,
``AvgA`` from 2019-20. Odds are optional: a match without all three is left out, a malformed or
impossible value (at most 1) is an error. The implied probabilities are 1 / odds, which sum to
more than 1 (the bookmakers' margin); the margin is removed proportionally:

    p_c = (1 / o_c) / sum_k (1 / o_k)        for c in home, draw, away
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

import pandas as pd

from app.data.preprocessing import DataValidationError, parse_match_date

# The market-average columns, the newest first; a file holds one of the two families
MARKET_COLUMNS = (("AvgH", "AvgD", "AvgA"), ("BbAvH", "BbAvD", "BbAvA"))


@dataclass(frozen=True, slots=True)
class MarketOdds:
    """The average decimal odds of one match's home win, draw and away win."""

    competition: str
    match_date: date
    home_team: str
    away_team: str
    home: float
    draw: float
    away: float

    def __post_init__(self) -> None:
        for name in ("home", "draw", "away"):
            value = getattr(self, name)
            if not (math.isfinite(value) and value > 1):
                raise ValueError(f"decimal odds must be above 1, got {name} {value}")

    @property
    def key(self) -> tuple[date, str, str]:
        return self.match_date, self.home_team, self.away_team

    def probabilities(self) -> tuple[float, float, float]:
        """The implied (home, draw, away) probabilities, the margin removed proportionally."""
        inverse = (1 / self.home, 1 / self.draw, 1 / self.away)
        total = sum(inverse)
        return inverse[0] / total, inverse[1] / total, inverse[2] / total


def market_columns(columns: list[str]) -> tuple[str, str, str] | None:
    """The market-average columns a file has, or None without any."""
    return next((family for family in MARKET_COLUMNS if all(c in columns for c in family)), None)


def odds_from_frame(frame: pd.DataFrame, source: str) -> list[MarketOdds]:
    """The market odds of a raw season file's matches (``frame`` as ``read_raw_season`` gives
    it); empty without the columns, and a match whose three cells are not all filled is left
    out. Malformed values are reported together, by line, in one DataValidationError."""
    family = market_columns(list(frame.columns))
    if family is None:
        return []
    found, problems = [], []
    for position, row in enumerate(frame.to_dict("records")):
        cells = [row[column].strip() for column in family]
        if not all(cells):
            continue
        try:
            home, draw, away = (float(cell) for cell in cells)
            found.append(
                MarketOdds(
                    competition=row["Div"].strip(),
                    match_date=parse_match_date(row["Date"].strip()),
                    home_team=row["HomeTeam"].strip(),
                    away_team=row["AwayTeam"].strip(),
                    home=home,
                    draw=draw,
                    away=away,
                )
            )
        except ValueError as error:
            problems.append(f"line {position + 2}: {error}")
    if problems:
        raise DataValidationError(f"{source}: market odds\n" + "\n".join(problems))
    return found


def odds_by_match(odds: list[MarketOdds]) -> Mapping[tuple[date, str, str], MarketOdds]:
    """The odds keyed by (date, home team, away team)."""
    return {item.key: item for item in odds}
