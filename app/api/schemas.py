"""The shapes of the server's answers. Numbers stay numbers (the interface formats them in
Romanian); names a person reads (models, outcomes, countries) come translated, from
``app/services/labels.py``."""

from datetime import date, datetime

from pydantic import BaseModel

from app.prediction.outputs import ModelPrediction
from app.services.labels import model_label
from app.services.predictions import MatchForecast


class League(BaseModel):
    code: str
    name: str
    country: str
    seasons: list[str]
    current_season: str | None
    updated_at: datetime | None
    prepared: bool
    photo_credit: str | None
    photo_top: float
    problem: str | None  # why the season in progress could not be read


class Status(BaseModel):
    prepared: dict[str, bool]
    preparing: str | None
    failures: dict[str, str]


class Prediction(BaseModel):
    model: str  # the identifier: Elo, Poisson, Logistic regression
    label: str  # the Romanian name
    home: float
    draw: float
    away: float
    most_likely: str  # H, D or A
    hit: bool | None  # whether the most likely outcome happened; None before the match
    expected_goals: tuple[float, float] | None


class Forecast(BaseModel):
    competition: str
    season: str
    date: date
    kickoff: str | None  # HH:MM, local time
    home_team: str
    away_team: str
    home_goals: int | None
    away_goals: int | None
    result: str | None  # H, D or A, once played
    postponed: bool
    as_of: date | None  # scheduled: the predictions use the matches before this day
    hypothetical: bool
    predictions: list[Prediction]


class LeagueDay(BaseModel):
    code: str
    name: str
    country: str
    prepared: bool
    forecasts: list[Forecast]


class Day(BaseModel):
    day: date
    leagues: list[LeagueDay]
    featured: Forecast | None


class Days(BaseModel):
    days: list[date]
    today: date
    next_day: date | None


class Favourite(BaseModel):
    competition: str
    team: str


class Preferences(BaseModel):
    competition: str | None
    favourite: Favourite | None


def prediction_of(prediction: ModelPrediction, forecast: MatchForecast) -> Prediction:
    probabilities = prediction.probabilities
    played = forecast.played
    most_likely = probabilities.most_likely
    return Prediction(
        model=str(prediction.model),
        label=model_label(str(prediction.model)),
        home=probabilities.home_win,
        draw=probabilities.draw,
        away=probabilities.away_win,
        most_likely=most_likely.value,
        hit=None if played is None else most_likely == played.result,
        expected_goals=prediction.expected_goals,
    )


def forecast_of(forecast: MatchForecast) -> Forecast:
    played = forecast.played
    return Forecast(
        competition=forecast.competition,
        season=forecast.season,
        date=forecast.match_date,
        kickoff=None if forecast.kickoff_time is None else f"{forecast.kickoff_time:%H:%M}",
        home_team=forecast.home_team,
        away_team=forecast.away_team,
        home_goals=None if played is None else played.home_goals,
        away_goals=None if played is None else played.away_goals,
        result=None if played is None else played.result.value,
        postponed=forecast.postponed,
        as_of=forecast.as_of,
        hypothetical=forecast.hypothetical,
        predictions=[prediction_of(p, forecast) for p in forecast.predictions.values()],
    )
