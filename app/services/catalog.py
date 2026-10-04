"""The data the user can choose from: one competition's seasons, teams and matches."""

from dataclasses import dataclass
from pathlib import Path

from app.data.models import Match
from app.data.paths import DATABASE_PATH
from app.data.repository import MatchRepository

DEFAULT_COMPETITION = "SP1"
COMPETITION_NAMES = {"SP1": "La Liga"}


@dataclass(frozen=True, slots=True)
class CatalogSummary:
    """What the loaded data covers."""

    competition: str
    competition_name: str
    seasons: int
    first_season: str
    last_season: str
    matches: int
    teams: int


class DataCatalog:
    """All matches of one competition, loaded once from the database."""

    def __init__(self, competition: str, matches: list[Match]) -> None:
        if not matches:
            raise ValueError(f"no matches for competition {competition!r}")
        self.competition = competition
        self.matches: tuple[Match, ...] = tuple(matches)

    @classmethod
    def load(
        cls, database_path: Path = DATABASE_PATH, competition: str = DEFAULT_COMPETITION
    ) -> DataCatalog:
        """Read the competition from the database built by ``python -m app.data.build_database``."""
        if not database_path.is_file():
            raise FileNotFoundError(
                f"Database not found: {database_path}. Run: python -m app.data.build_database"
            )
        with MatchRepository.open(database_path) as repository:
            return cls(competition, repository.matches(competition))

    def seasons(self) -> list[str]:
        return sorted({match.season for match in self.matches})

    def teams(self, season: str) -> list[str]:
        return sorted(
            {team for m in self.season_matches(season) for team in (m.home_team, m.away_team)}
        )

    def season_matches(self, season: str) -> list[Match]:
        """The matches of a season in chronological order."""
        selected = [match for match in self.matches if match.season == season]
        if not selected:
            raise ValueError(f"no matches in season {season!r}")
        return selected

    def summary(self) -> CatalogSummary:
        seasons = self.seasons()
        teams = {team for m in self.matches for team in (m.home_team, m.away_team)}
        return CatalogSummary(
            competition=self.competition,
            competition_name=COMPETITION_NAMES.get(self.competition, self.competition),
            seasons=len(seasons),
            first_season=seasons[0],
            last_season=seasons[-1],
            matches=len(self.matches),
            teams=len(teams),
        )
