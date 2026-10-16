"""The data the user can choose from: the leagues in the database, and one league's seasons,
teams and matches.

The database holds the completed seasons. The season in progress (Phase 18), when it was
downloaded, is added to them: its matches played so far and the matches still to be played.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from app.data.competitions import COMPETITIONS
from app.data.live import load_live_league
from app.data.models import Fixture, Match
from app.data.paths import DATABASE_PATH
from app.data.preprocessing import DataValidationError, season_date_window
from app.data.repository import MatchRepository

DEFAULT_COMPETITION = "SP1"


def available_competitions(database_path: Path = DATABASE_PATH) -> list[str]:
    """The known leagues stored in the database, in the order of ``COMPETITIONS``."""
    if not database_path.is_file():
        raise FileNotFoundError(
            f"Database not found: {database_path}. Run: python -m app.data.build_database"
        )
    with MatchRepository.open(database_path) as repository:
        stored = set(repository.competitions())
    return [code for code in COMPETITIONS if code in stored]


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
    """All matches of one competition, loaded once: the completed seasons from the database and,
    when it was downloaded, the season in progress with its fixtures."""

    def __init__(
        self,
        competition: str,
        matches: list[Match],
        fixtures: tuple[Fixture, ...] = (),
        *,
        current_season: str | None = None,
        updated_at: datetime | None = None,
        unmatched_teams: tuple[str, ...] = (),
        live_problem: str | None = None,
    ) -> None:
        if not matches:
            raise ValueError(f"no matches for competition {competition!r}")
        if fixtures and current_season is None:
            raise ValueError("fixtures need the season in progress")
        if any(fixture.season != current_season for fixture in fixtures):
            raise ValueError(f"every fixture must belong to season {current_season}")
        self.competition = competition
        self.matches: tuple[Match, ...] = tuple(matches)
        self.fixtures = fixtures
        self.current_season = current_season  # the season in progress, None when not downloaded
        self.updated_at = updated_at  # when the season in progress was downloaded (UTC)
        self.unmatched_teams = unmatched_teams  # calendar names whose fixtures are left out
        self.live_problem = live_problem  # why the downloaded season could not be used

    @classmethod
    def load(
        cls,
        database_path: Path = DATABASE_PATH,
        competition: str = DEFAULT_COMPETITION,
        live_dir: Path | None = None,
    ) -> DataCatalog:
        """Read the competition from the database built by ``python -m app.data.build_database``,
        and its season in progress from ``live_dir`` when given.

        Damaged files of the season in progress do not stop the league from opening: the
        completed seasons are shown and ``live_problem`` says what went wrong.
        """
        if not database_path.is_file():
            raise FileNotFoundError(
                f"Database not found: {database_path}. Run: python -m app.data.build_database"
            )
        with MatchRepository.open(database_path) as repository:
            matches = repository.matches(competition)
        if live_dir is None or not matches:
            return cls(competition, matches)
        try:
            live = load_live_league(competition, live_dir)
        except (DataValidationError, OSError) as error:
            return cls(competition, matches, live_problem=str(error))
        if live is None or not live.matches or live.season <= matches[-1].season:
            return cls(competition, matches)  # nothing played yet, or the season is complete
        return cls(
            competition,
            [*matches, *live.matches],
            live.fixtures,
            current_season=live.season,
            updated_at=live.updated_at,
            unmatched_teams=live.unmatched_teams,
        )

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

    def hypothetical_days(self, season: str) -> tuple[date, date, date]:
        """The days a hypothetical match of the season may be on (first, last) and the day
        offered first: the day after the last match played in the season in progress, the
        middle of a completed season."""
        first_day, last_day = season_date_window(season)
        days = [match.match_date for match in self.season_matches(season)]
        if season == self.current_season:
            return first_day, last_day, max(days) + timedelta(days=1)
        return first_day, last_day, days[len(days) // 2]

    def summary(self) -> CatalogSummary:
        seasons = self.seasons()
        teams = {team for m in self.matches for team in (m.home_team, m.away_team)}
        return CatalogSummary(
            competition=self.competition,
            competition_name=(
                COMPETITIONS[self.competition].name
                if self.competition in COMPETITIONS
                else self.competition
            ),
            seasons=len(seasons),
            first_season=seasons[0],
            last_season=seasons[-1],
            matches=len(self.matches),
            teams=len(teams),
        )
