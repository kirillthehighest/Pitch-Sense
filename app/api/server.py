"""The routes of the local server (FastAPI). Each one reads the services through ``Backend`` and
answers in the shapes of ``schemas.py``; the server listens on this computer only."""

from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import __version__
from app.api import schemas
from app.api.analysis import add_analysis_routes
from app.api.backend import Backend
from app.data.competitions import competition
from app.data.models import Outcome
from app.prediction.outputs import ModelName
from app.services.explanations import (
    GROUPS_IN_PROGRESS,
    GROUPS_NO_STATISTICS,
    MODEL_EXPLANATIONS,
    knowledge_text,
    status_text,
    verdict_text,
)
from app.services.images import (
    crest_path,
    league_photo_path,
    photo_credit,
    photo_top,
    stadium_name,
    stadium_path,
)
from app.services.labels import country_label, model_label, outcome_label
from app.services.predictions import (
    SURPRISE_CHANCE,
    MatchForecast,
    featured_match,
    forecast_of,
    summarize,
)
from app.services.preferences import FavouriteTeam
from app.services.teams import GROUP_NAMES
from app.services.updates import summary_text

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
        """One day's matches, the chosen league first, and the chosen league's match of the day:
        on this day, else on its nearest day with matches (the interface says which)."""
        chosen = league or backend.first_league
        codes = [chosen, *(code for code in backend.competitions if code != chosen)]
        groups = []
        for code in codes:
            services = league_of(code)
            ready = services.predictions.is_prepared
            forecasts = services.predictions.on_day(day) if ready else []
            if ready and not forecasts:
                continue
            groups.append(
                schemas.LeagueDay(
                    code=code,
                    name=competition(code).name,
                    country=country_label(code),
                    prepared=ready,
                    forecasts=[schemas.forecast_of(f) for f in forecasts],
                )
            )
        featured = None
        chosen_predictions = league_of(chosen).predictions
        if chosen_predictions.is_prepared:  # the chosen league's match, on its nearest match day
            featured_day = chosen_predictions.nearest_match_day(day)
            if featured_day is not None:
                teams = league_of(chosen).teams

                def strength(forecast) -> float:
                    total = 0.0
                    for team in (forecast.home_team, forecast.away_team):
                        try:
                            total += teams.rating_before(team, featured_day)
                        except ValueError:  # a team without a match yet: no rating
                            pass
                    return total

                favourite = backend.preferences.favourite
                followed = favourite.team if favourite and favourite.competition == chosen else None
                featured = featured_match(
                    chosen_predictions.on_day(featured_day), strength, followed
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

    @app.get("/api/season/{code}", response_model=schemas.SeasonDays)
    def season_days(code: str, season: str | None = None) -> schemas.SeasonDays:
        services = league_of(code)
        season = season_of(services, season)
        first_day, last_day, suggested = services.catalog.hypothetical_days(season)
        return schemas.SeasonDays(
            season=season,
            teams=services.catalog.teams(season),
            first_day=first_day,
            last_day=last_day,
            suggested_day=suggested,
        )

    def find_forecast(services, season: str, day: date, home: str, away: str) -> MatchForecast:
        """The match of the calendar, or a hypothetical match predicted on request."""
        listed = services.predictions.on_day(day)
        found = next(
            (f for f in listed if (f.season, f.home_team, f.away_team) == (season, home, away)),
            None,
        )
        if found is not None:
            return found
        teams = services.catalog.teams(season)
        if home not in teams or away not in teams:
            missing = home if home not in teams else away
            raise HTTPException(404, f"no team {missing!r} in season {season}")
        try:
            return forecast_of(services.predictions.predict(season, home, away, day), services.code)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    def team_state(services, season: str, team: str, before: date) -> schemas.TeamState:
        overview = services.teams.overview(season, team, before)
        return schemas.TeamState(
            team=team,
            position=overview.position,
            record=schemas.record_of(overview.record),
            form=[result.value for result in overview.form],
            rating=services.teams.rating_before(team, before),
        )

    @app.get("/api/match/{code}", response_model=schemas.MatchPage)
    def match(code: str, season: str, day: date, home: str, away: str) -> schemas.MatchPage:
        """Everything about one match: of the calendar, played or not, or any two teams of a
        season on a day of it (a hypothetical match)."""
        services = league_of(code)
        season = season_of(services, season)
        if home == away:
            raise HTTPException(422, "a match needs two different teams")
        if not services.predictions.is_prepared:
            raise HTTPException(409, f"the predictions of {code} are being prepared")
        forecast = find_forecast(services, season, day, home, away)
        played = forecast.played is not None
        before = forecast.match_date if played or not forecast.as_of else forecast.as_of
        poisson = next(
            (
                summarize(p)
                for p in forecast.predictions.values()
                if p.score_distribution is not None
            ),
            None,
        )
        return schemas.MatchPage(
            forecast=schemas.forecast_of(forecast),
            status=status_text(forecast),
            knowledge=knowledge_text(forecast),
            verdict=verdict_text(forecast) if played and forecast.predictions else None,
            explanations={str(model): text for model, text in MODEL_EXPLANATIONS.items()},
            poisson=None if poisson is None else schemas.poisson_of(poisson),
            before=before,
            teams=len(services.teams.standings(season)),
            home=team_state(services, season, home, before),
            away=team_state(services, season, away, before),
            stadium=stadium_name(home),
        )

    def groups_of(services, season: str) -> tuple[schemas.Groups | None, str | None]:
        if season == services.teams.in_progress:
            return None, GROUPS_IN_PROGRESS
        try:
            found = services.teams.season_groups(season)
        except ValueError:  # a season without shot statistics has no groups
            return None, GROUPS_NO_STATISTICS
        return (
            schemas.Groups(
                teams=[
                    schemas.GroupPoint(
                        team=p.team,
                        goals_scored=p.goals_scored,
                        goals_conceded=p.goals_conceded,
                        group=p.group,
                    )
                    for p in found.teams
                ],
                centres=[
                    schemas.GroupCentre(
                        group=c.group, goals_scored=c.goals_scored, goals_conceded=c.goals_conceded
                    )
                    for c in found.centres
                ],
                names=GROUP_NAMES,
            ),
            None,
        )

    @app.get("/api/team/{code}", response_model=schemas.TeamPage)
    def team_page(code: str, season: str | None = None, team: str | None = None):
        """A club's season: without a team, "your team" if it played the season, else the
        leader."""
        services = league_of(code)
        season = season_of(services, season)
        teams = services.teams
        if team is None:
            favourite = backend.preferences.favourite
            played = services.catalog.teams(season)
            if favourite and favourite.competition == code and favourite.team in played:
                team = favourite.team
            else:
                team = teams.standings(season)[0].team
        try:
            overview = teams.overview(season, team)
        except ValueError as error:
            raise HTTPException(404, str(error)) from None
        statistics = overview.match_statistics
        groups, problem = groups_of(services, season)
        return schemas.TeamPage(
            competition=code,
            team=team,
            season=season,
            position=overview.position,
            teams=len(teams.standings(season)),
            in_progress=overview.in_progress,
            record=schemas.record_of(overview.record),
            home=schemas.record_of(overview.home),
            away=schemas.record_of(overview.away),
            form=[result.value for result in overview.form],
            shots=schemas.Shots(
                matches=statistics.matches_with_statistics,
                shots=statistics.shots,
                opponent_shots=statistics.opponent_shots,
                shots_on_target=statistics.shots_on_target,
                opponent_shots_on_target=statistics.opponent_shots_on_target,
            ),
            pre_season_group=overview.pre_season_group,
            season_group=overview.season_group,
            elo=[
                schemas.RatingSeason(
                    season=history.season,
                    points=[
                        schemas.RatingPoint(day=day, rating=rating)
                        for day, rating in zip(history.dates, history.ratings, strict=True)
                    ],
                )
                for history in teams.elo_history(team)
            ],
            groups=groups,
            groups_problem=problem,
            stadium=stadium_name(team),
        )

    @app.get("/api/review/{code}", response_model=schemas.Review)
    def review(code: str, model: str, season: str | None = None) -> schemas.Review:
        """What a model predicted for a season's played matches and what happened."""
        services = league_of(code)
        season = season_of(services, season)
        try:
            chosen = ModelName(model)
        except ValueError:
            raise HTTPException(404, f"no model {model!r}") from None
        if not services.predictions.is_prepared:
            raise HTTPException(409, f"the predictions of {code} are being prepared")
        found = services.predictions.review(season, chosen)
        by_result = found.by_result()
        return schemas.Review(
            competition=code,
            season=season,
            model=str(chosen),
            label=model_label(str(chosen)),
            surprise_chance=SURPRISE_CHANCE,
            matches=len(found.matches),
            hits=found.hits,
            surprises=found.surprises,
            by_result=[
                schemas.ResultReview(
                    result=outcome.value,
                    label=outcome_label(outcome.value),
                    hits=by_result[outcome][0],
                    matches=by_result[outcome][1],
                )
                for outcome in (Outcome.HOME_WIN, Outcome.DRAW, Outcome.AWAY_WIN)
            ],
            rows=[
                schemas.ReviewedMatch(
                    forecast=schemas.forecast_of(row.forecast),
                    chance=row.chance,
                    hit=row.hit,
                    surprise=row.surprise,
                )
                for row in found.matches
            ],
        )

    @app.post("/api/update", response_model=schemas.Update)
    def update() -> schemas.Update:
        """Download the season in progress (the network, on the user's request only), then read
        every league again and prepare its predictions again."""
        try:
            summary = backend.update_data()
        except Exception as error:  # the previous data stays; the interface explains in Romanian
            raise HTTPException(502, str(error)) from None
        backend.reload()
        return schemas.Update(summary=summary_text(summary))

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

    add_analysis_routes(app, backend, league_of)

    @app.get("/api/images/crest/{team}")
    def crest(team: str) -> FileResponse:
        path = crest_path(team)
        if path is None:
            raise HTTPException(404, f"no crest for {team!r}")
        return FileResponse(path, media_type="image/png")

    @app.get("/api/images/stadium/{team}")
    def stadium(team: str) -> FileResponse:
        path = stadium_path(team)
        if path is None:
            raise HTTPException(404, f"no stadium photo for {team!r}")
        return FileResponse(path, media_type="image/jpeg")

    @app.get("/api/images/league/{code}")
    def league_photo(code: str) -> FileResponse:
        path = league_photo_path(code)
        if path is None:
            raise HTTPException(404, f"no image for {code!r}")
        return FileResponse(path, media_type="image/jpeg")

    return app
