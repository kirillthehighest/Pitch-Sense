"""The shapes of the server's answers. Numbers stay numbers (the interface formats them in
Romanian); names a person reads (models, outcomes, countries) come translated, from
``app/services/labels.py``."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.prediction.outputs import ModelPrediction
from app.services.labels import model_label
from app.services.predictions import MatchForecast, ModelSummary
from app.statistics.team_statistics import TeamStatistics

SCORE_GRID_GOALS = 6  # the scores 0-0 to 6-6, the grid of a match page


class Schema(BaseModel):
    """An answer of the server; a field it does not declare is an error, never dropped."""

    model_config = ConfigDict(extra="forbid")


class League(Schema):
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


class Status(Schema):
    prepared: dict[str, bool]
    preparing: str | None
    failures: dict[str, str]
    version: int  # grows when a league's data is replaced after an update (Phase 24)
    updating: bool  # an update, the user's or the automatic one, is downloading


class Prediction(Schema):
    model: str  # the identifier: Elo, Poisson, Logistic regression
    label: str  # the Romanian name
    home: float
    draw: float
    away: float
    most_likely: str  # H, D or A
    hit: bool | None  # whether the most likely outcome happened; None before the match
    expected_goals: tuple[float, float] | None


class Forecast(Schema):
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


class LeagueDay(Schema):
    code: str
    name: str
    country: str
    prepared: bool
    forecasts: list[Forecast]


class Day(Schema):
    day: date
    leagues: list[LeagueDay]
    featured: Forecast | None


class Days(Schema):
    days: list[date]
    today: date
    next_day: date | None


class Record(Schema):
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int


class StandingRow(Schema):
    position: int
    team: str
    record: Record
    form: list[str]  # the last five results, W, D or L, oldest first


class Standings(Schema):
    competition: str
    season: str
    before: date
    whole_season: bool
    in_progress: bool
    rows: list[StandingRow]


class TeamState(Schema):
    """How a team came into a match: its place, season so far, form and Elo rating."""

    team: str
    position: int
    record: Record
    form: list[str]
    rating: float


class ScoreChance(Schema):
    home: int
    away: int
    probability: float


class PoissonScores(Schema):
    expected_goals: tuple[float, float]
    top_scores: list[ScoreChance]
    grid: list[list[float]]  # grid[i][j]: the home team scores i and the away team j


class MatchPage(Schema):
    forecast: Forecast
    status: str  # Final, Programat, Amânat or Meci ipotetic
    knowledge: str  # which matches the predictions use
    verdict: str | None  # once played: the result and which models expected it
    explanations: dict[str, str]  # what each model looks at, by model identifier
    poisson: PoissonScores | None
    before: date  # the teams' state is the one before this day
    teams: int  # in the season
    home: TeamState
    away: TeamState
    stadium: str | None  # the home club's ground, when its photo is known


class Shots(Schema):
    """A team's averages per match, its own and its opponents' (None without statistics)."""

    matches: int  # with recorded statistics
    shots: float | None
    opponent_shots: float | None
    shots_on_target: float | None
    opponent_shots_on_target: float | None


class RatingPoint(Schema):
    day: date
    rating: float


class RatingSeason(Schema):
    season: str
    points: list[RatingPoint]  # the Elo rating before each of the team's matches


class GroupPoint(Schema):
    team: str
    goals_scored: float
    goals_conceded: float
    group: int


class GroupCentre(Schema):
    group: int
    goals_scored: float
    goals_conceded: float


class Groups(Schema):
    """A completed season's descriptive K-Means groups, in goals per match."""

    teams: list[GroupPoint]
    centres: list[GroupCentre]
    names: dict[int, str]


class TeamPage(Schema):
    competition: str
    team: str
    season: str
    position: int
    teams: int
    in_progress: bool
    record: Record
    home: Record
    away: Record
    form: list[str]
    shots: Shots
    pre_season_group: str
    season_group: str | None  # None until the season is over
    elo: list[RatingSeason]
    groups: Groups | None
    groups_problem: str | None
    stadium: str | None  # the club's ground, when its photo is known
    first_evaluated_season: str  # earlier seasons only start the models (warm-up, calibration)


class ReviewedMatch(Schema):
    forecast: Forecast
    chance: float  # the probability the model gave the result that happened
    hit: bool
    surprise: bool
    confidence: float  # the model's largest probability


class SureReview(Schema):
    threshold: float
    hits: int
    matches: int


class ResultReview(Schema):
    result: str  # H, D or A
    label: str
    hits: int
    matches: int


class Review(Schema):
    """One model's predictions of a season's played matches, against what happened."""

    competition: str
    season: str
    model: str
    label: str
    surprise_chance: float  # a result with less chance than this is a surprise
    matches: int
    hits: int
    surprises: int
    by_result: list[ResultReview]
    sure: list[SureReview]  # when the model was sure (Phase 23)
    rows: list[ReviewedMatch]


class ModelRecord(Schema):
    model: str
    label: str
    hits: int
    matches: int
    recent_hits: int  # over the latest week of matches
    recent_matches: int


class TrackRecord(Schema):
    """How often each model has been right this season, in all and over its latest week."""

    competition: str
    season: str
    in_progress: bool
    last_day: date | None
    recent_from: date | None
    models: list[ModelRecord]


class ProjectedTeam(Schema):
    team: str
    position: int
    played: int
    points: int
    goal_difference: int
    remaining: int
    expected_points: float
    places: list[float]  # the chance of each final place, first to last
    top: float
    bottom: float


class Projection(Schema):
    """The rest of the season played many times from one model's predictions (Phase 25)."""

    competition: str
    season: str
    model: str
    label: str
    simulations: int
    fixtures: int
    unpredicted: int  # fixtures the model has no prediction for, left out
    top_places: int
    bottom_places: int
    teams: list[ProjectedTeam]


class SeasonDays(Schema):
    """What the form of a hypothetical match offers for a season."""

    season: str
    teams: list[str]
    first_day: date
    last_day: date
    suggested_day: date


class Update(Schema):
    summary: str  # what the update brought, in Romanian


class Favourite(Schema):
    competition: str
    team: str


class Preferences(Schema):
    competition: str | None
    favourite: Favourite | None


def record_of(record: TeamStatistics) -> Record:
    return Record(
        played=record.played,
        wins=record.wins,
        draws=record.draws,
        losses=record.losses,
        goals_for=record.goals_for,
        goals_against=record.goals_against,
        goal_difference=record.goal_difference,
        points=record.points,
    )


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


def poisson_of(summary: ModelSummary) -> PoissonScores:
    shown = summary.score_probabilities[: SCORE_GRID_GOALS + 1, : SCORE_GRID_GOALS + 1]
    return PoissonScores(
        expected_goals=summary.expected_goals,
        top_scores=[ScoreChance(home=h, away=a, probability=p) for h, a, p in summary.top_scores],
        grid=shown.tolist(),
    )


# --- Analiză ---


class Text(Schema):
    title: str
    text: str


class About(Schema):
    """How the algorithms work and where the data and images come from."""

    explanations: list[Text]
    groups: str  # what the K-Means profiles of the team pages are
    sources: list[Text]
    crests: int
    stadiums: int  # stadium photos
    photos: list[str]
    images_note: str


class Estimate(Schema):
    value: float
    margin: float | None  # the half-width of the 95% interval: 1.96 standard errors


class ModelCheck(Schema):
    model: str
    label: str
    accuracy: float
    brier: Estimate
    log_loss: Estimate


class SeasonCheck(Schema):
    """The models on the season in progress, or why they cannot be shown yet."""

    competition: str
    season: str | None
    state: str  # ready, missing (not downloaded), preparing, empty (nothing predicted yet)
    matches: int
    first_day: date | None
    last_day: date | None
    models: list[ModelCheck]


class Difference(Schema):
    """A paired per-match difference between two models (first minus second)."""

    first: str
    second: str
    first_label: str
    second_label: str
    measure: str
    measure_label: str
    mean: float
    lower: float
    upper: float
    better: str | None  # the model really better (its 95% interval excludes 0)
    better_label: str | None


class CalibrationBin(Schema):
    lower: float
    upper: float
    count: int
    predicted: float | None
    observed: float | None


class ConfidentAccuracy(Schema):
    """Among the matches the model gave at least ``threshold`` to its most likely outcome."""

    threshold: float
    matches: int
    share: float  # of all the matches
    accuracy: float | None  # None without such matches


class ModelEvaluation(Schema):
    model: str
    label: str
    matches: int
    accuracy: float
    brier: float | None
    log_loss: float | None
    calibration_error: float | None
    goals_error: float | None
    calibration: list[CalibrationBin] | None
    confusion: list[list[int]]  # rows actual, columns predicted: H, D, A
    confident: list[ConfidentAccuracy]  # when the model is sure (Phase 23)


class Subset(Schema):
    key: str
    label: str
    matches: int
    brier: dict[str, float]
    best: str
    best_label: str
    real: bool  # the best model's lead over the runner-up is real


class Agreement(Schema):
    first: str
    second: str
    first_label: str
    second_label: str
    same: float  # the share of matches with the same predicted result
    distance: float  # the mean total variation distance


class BookmakerComparison(Schema):
    """The models and the bookmakers' odds on the evaluation matches with odds (Phase 23)."""

    matches: int
    missing: int
    models: list[ModelEvaluation]  # the models, then the bookmakers
    differences: list[Difference]  # Brier score, each model minus the bookmakers


class Evaluation(Schema):
    """A league's chronological backtest, evaluated and compared."""

    competition: str
    has_log: bool
    problem: str | None  # why the log cannot be read
    matches: int
    first_season: str | None
    last_season: str | None
    compared: list[str]  # the compared models, then the reference, in order
    models: list[ModelEvaluation]
    differences: list[Difference]
    by_season: list[Subset]
    by_outcome: list[Subset]
    by_matchup_type: list[Subset]
    agreements: list[Agreement]
    all_agree: float | None
    bookmakers: BookmakerComparison | None


class Character(Schema):
    matches: int
    home_win: float
    draw: float
    away_win: float
    goals: float
    home_margin: float
    closed_doors_home_win: float | None
    other_seasons_home_win: float | None


class LeagueResult(Schema):
    code: str
    name: str
    character: Character
    brier: dict[str, float]
    best: str
    best_label: str
    skill: dict[str, float]
    differences: list[Difference]


class LeaguesComparison(Schema):
    missing: list[str]  # leagues without a prediction log
    problem: str | None
    matches: int
    compared: list[str]
    reference: str
    results: list[LeagueResult]
    pooled: list[Difference]
