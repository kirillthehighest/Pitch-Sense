"""The competitions PitchSense knows, and the shape of each of their seasons.

Every season is a double round-robin, so its size follows from the number of teams. Two facts
change from one season to another and are listed per competition: a different number of teams
(Ligue 1 went from 20 to 18 teams in 2023/24) and a season stopped before its end (Ligue 1
2019/20 ended after 279 matches because of COVID-19; the table was settled on points per match).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Competition:
    """One league: its Football-Data.co.uk code (``Div``), its name and its usual size."""

    code: str
    name: str
    teams: int  # in every season not listed in team_changes
    team_changes: Mapping[str, int] = field(default_factory=dict)  # season -> teams
    stopped_early: Mapping[str, int] = field(default_factory=dict)  # season -> matches played

    def __post_init__(self) -> None:
        if self.teams < 2 or any(count < 2 for count in self.team_changes.values()):
            raise ValueError(f"{self.code}: a league needs at least two teams")

    def teams_in(self, season: str) -> int:
        return self.team_changes.get(season, self.teams)

    @property
    def season_length(self) -> int:
        """The matches of one usual season; model windows of "one season" use this size."""
        return self.teams * (self.teams - 1)

    @property
    def venue_season_length(self) -> int:
        """The home (or away) matches of one team in a usual season."""
        return self.teams - 1


COMPETITIONS: Mapping[str, Competition] = {
    competition.code: competition
    for competition in (
        Competition("E0", "Premier League", 20),
        Competition("SP1", "La Liga", 20),
        Competition("I1", "Serie A", 20),
        Competition("D1", "Bundesliga", 18),
        Competition(
            "F1",
            "Ligue 1",
            20,
            team_changes={"2023-24": 18, "2024-25": 18, "2025-26": 18},
            stopped_early={"2019-20": 279},
        ),
    )
}


def competition(code: str) -> Competition:
    """The competition with this code; an unknown code is an error, not a guess."""
    try:
        return COMPETITIONS[code]
    except KeyError:
        known = ", ".join(COMPETITIONS)
        raise ValueError(f"unknown competition {code!r} (known: {known})") from None
