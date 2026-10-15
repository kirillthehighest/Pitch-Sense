"""Domain records: matches already played and matches still to play."""

from dataclasses import dataclass, fields
from datetime import date, time
from enum import StrEnum


class Outcome(StrEnum):
    """Full-time result from the home side's point of view, using the source data's codes."""

    HOME_WIN = "H"
    DRAW = "D"
    AWAY_WIN = "A"

    @classmethod
    def from_score(cls, home_goals: int, away_goals: int) -> Outcome:
        """Return the outcome implied by a full-time score."""
        if home_goals > away_goals:
            return cls.HOME_WIN
        if home_goals < away_goals:
            return cls.AWAY_WIN
        return cls.DRAW


@dataclass(frozen=True, slots=True)
class MatchStatistics:
    """Post-match statistics of one match.

    They describe the match itself, so they are never known before kickoff. They may only feed
    predictions of later matches.
    """

    home_shots: int
    away_shots: int
    home_shots_on_target: int
    away_shots_on_target: int
    home_fouls: int
    away_fouls: int
    home_corners: int
    away_corners: int
    home_yellow_cards: int
    away_yellow_cards: int
    home_red_cards: int
    away_red_cards: int

    def __post_init__(self) -> None:
        negative = [field.name for field in fields(self) if getattr(self, field.name) < 0]
        if negative:
            raise ValueError(f"statistics cannot be negative: {', '.join(negative)}")


@dataclass(frozen=True, slots=True)
class Match:
    """One played match, as recorded in the source data. Every instance is internally consistent."""

    competition: str
    season: str
    match_date: date
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    result: Outcome
    kickoff_time: time | None = None
    statistics: MatchStatistics | None = None

    def __post_init__(self) -> None:
        if not self.competition or not self.season:
            raise ValueError("competition and season cannot be empty")
        if not self.home_team or not self.away_team:
            raise ValueError("team names cannot be empty")
        if self.home_team == self.away_team:
            raise ValueError(f"a team cannot play itself: {self.home_team!r}")
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError(f"goals cannot be negative: {self.home_goals}-{self.away_goals}")
        if self.result != Outcome.from_score(self.home_goals, self.away_goals):
            raise ValueError(
                f"result {self.result} does not match score {self.home_goals}-{self.away_goals}"
            )


@dataclass(frozen=True, slots=True)
class Fixture:
    """A match scheduled but not played yet: its teams, its date and, when known, its kickoff.

    It has no score and no statistics, so nothing about the match itself can reach a prediction.
    """

    competition: str
    season: str
    match_date: date
    home_team: str
    away_team: str
    kickoff_time: time | None = None

    def __post_init__(self) -> None:
        if not self.competition or not self.season:
            raise ValueError("competition and season cannot be empty")
        if not self.home_team or not self.away_team:
            raise ValueError("team names cannot be empty")
        if self.home_team == self.away_team:
            raise ValueError(f"a team cannot play itself: {self.home_team!r}")
