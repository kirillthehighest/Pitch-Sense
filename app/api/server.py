"""The routes of the local server (FastAPI). Each one reads the services through ``Backend`` and
answers in the shapes of ``schemas.py``; the server listens on this computer only."""

from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import __version__
from app.api import schemas
from app.api.backend import Backend
from app.data.competitions import competition
from app.services.images import crest_path, league_photo_path, photo_credit, photo_top
from app.services.labels import country_label
from app.services.predictions import featured_match
from app.services.preferences import FavouriteTeam

# The web interface is served by the desktop shell (Tauri) or, while developing, by Vite.
ORIGINS = ["tauri://localhost", "http://tauri.localhost", "http://localhost:1420"]


def create_app(backend: Backend) -> FastAPI:
    """The server over ``backend``."""
    app = FastAPI(title="PitchSense", version=__version__)
    app.add_middleware(
        CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"]
    )

    def league_of(code: str):
        try:
            return backend.league(code)
        except KeyError:
            raise HTTPException(404, f"no league {code!r}") from None

    @app.get("/api/leagues", response_model=list[schemas.League])
    def leagues() -> list[schemas.League]:
        answer = []
        for code in backend.competitions:
            league = league_of(code)
            catalog = league.catalog
            answer.append(
                schemas.League(
                    code=code,
                    name=competition(code).name,
                    country=country_label(code),
                    seasons=catalog.seasons(),
                    current_season=catalog.current_season,
                    updated_at=catalog.updated_at,
                    prepared=league.predictions.is_prepared,
                    photo_credit=photo_credit(code),
                    photo_top=photo_top(code),
                    problem=catalog.live_problem,
                )
            )
        return answer

    @app.get("/api/status", response_model=schemas.Status)
    def status() -> schemas.Status:
        return schemas.Status(
            prepared={code: backend.is_prepared(code) for code in backend.competitions},
            preparing=backend.preparing(),
            failures={c: f for c in backend.competitions if (f := backend.failure(c))},
        )

    @app.get("/api/days", response_model=schemas.Days)
    def days() -> schemas.Days:
        """Every day with a match in a league whose predictions are ready."""
        found = sorted(
            {
                day
                for code in backend.competitions
                if backend.is_prepared(code)
                for day in league_of(code).predictions.match_days()
            }
        )
        today = backend.today()
        next_day = next((day for day in found if day >= today), found[-1] if found else None)
        return schemas.Days(days=found, today=today, next_day=next_day)

    @app.get("/api/day/{day}", response_model=schemas.Day)
    def day_of(day: date, league: str | None = None) -> schemas.Day:
        """One day's matches, the chosen league first; the match of the day among them."""
        chosen = league or backend.first_league
        codes = [chosen, *(code for code in backend.competitions if code != chosen)]
        groups, everything = [], []
        for code in codes:
            services = league_of(code)
            ready = services.predictions.is_prepared
            forecasts = services.predictions.on_day(day) if ready else []
            if ready and not forecasts:
                continue
            everything.extend(forecasts)
            groups.append(
                schemas.LeagueDay(
                    code=code,
                    name=competition(code).name,
                    country=country_label(code),
                    prepared=ready,
                    forecasts=[schemas.forecast_of(f) for f in forecasts],
                )
            )
        favourite = backend.preferences.favourite

        def strength(forecast) -> float:
            teams = league_of(forecast.competition).teams
            total = 0.0
            for team in (forecast.home_team, forecast.away_team):
                try:
                    total += teams.rating_before(team, day)
                except ValueError:  # a team without a match yet: no rating
                    pass
            return total

        featured = featured_match(
            everything, chosen, strength, favourite.team if favourite else None
        )
        return schemas.Day(
            day=day,
            leagues=groups,
            featured=None if featured is None else schemas.forecast_of(featured),
        )

    def season_of(services, season: str | None) -> str:
        seasons = services.catalog.seasons()
        if season is None:
            return seasons[-1]
        if season not in seasons:
            raise HTTPException(404, f"no season {season!r}")
        return season

    @app.get("/api/standings/{code}", response_model=schemas.Standings)
    def standings(
        code: str, season: str | None = None, before: date | None = None
    ) -> schemas.Standings:
        """A season's table, at its end or before a day, with each team's form."""
        services = league_of(code)
        season = season_of(services, season)
        teams = services.teams
        end = teams.season_end(season)
        whole = before is None or before >= end
        day = end if whole else before
        rows = teams.standings(season, day)
        forms = {row.team: teams.form(row.team, day) for row in rows}  # as the window shows it
        return schemas.Standings(
            competition=code,
            season=season,
            before=day,
            whole_season=whole,
            in_progress=season == services.catalog.current_season,
            rows=[
                schemas.StandingRow(
                    position=row.position,
                    team=row.team,
                    record=schemas.record_of(row.record),
                    form=[result.value for result in forms[row.team]],
                )
                for row in rows
            ],
        )

    @app.get("/api/teams/{code}", response_model=list[str])
    def teams(code: str, season: str | None = None) -> list[str]:
        services = league_of(code)
        return services.catalog.teams(season_of(services, season))

    @app.get("/api/team-matches/{code}", response_model=list[schemas.Forecast])
    def team_matches(code: str, team: str, season: str | None = None) -> list[schemas.Forecast]:
        """A team's matches of one season, played and scheduled, once predictions are ready."""
        services = league_of(code)
        season = season_of(services, season)
        if not services.predictions.is_prepared:
            return []
        return [schemas.forecast_of(f) for f in services.predictions.team_matches(team, season)]

    @app.get("/api/preferences", response_model=schemas.Preferences)
    def preferences() -> schemas.Preferences:
        favourite = backend.preferences.favourite
        return schemas.Preferences(
            competition=backend.preferences.competition,
            favourite=None
            if favourite is None
            else schemas.Favourite(competition=favourite.competition, team=favourite.team),
        )

    @app.put("/api/preferences", response_model=schemas.Preferences)
    def set_preferences(choice: schemas.Preferences) -> schemas.Preferences:
        if choice.competition is not None:
            league_of(choice.competition)
            backend.preferences.set_competition(choice.competition)
        favourite = choice.favourite
        backend.preferences.set_favourite(
            None if favourite is None else FavouriteTeam(favourite.competition, favourite.team)
        )
        return preferences()

    @app.get("/api/images/crest/{team}")
    def crest(team: str) -> FileResponse:
        path = crest_path(team)
        if path is None:
            raise HTTPException(404, f"no crest for {team!r}")
        return FileResponse(path, media_type="image/png")

    @app.get("/api/images/league/{code}")
    def league_photo(code: str) -> FileResponse:
        path = league_photo_path(code)
        if path is None:
            raise HTTPException(404, f"no image for {code!r}")
        return FileResponse(path, media_type="image/jpeg")

    return app
