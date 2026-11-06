"""The season at a glance (Phase 25): how often each model has been right so far, and where the
table is heading.

``track_record`` sums a season's reviews: every model's hits over the whole season and over its
latest week of matches. ``project_table`` plays the rest of the season many times from the
predictions already made for its fixtures: each match ends as a home win, a draw or an away win
with the model's own probabilities, independently of the others. Counting where each club
finishes gives its expected points and its chance of every place. Only results are simulated,
not goals, so clubs level on points keep the order of their goal difference and goals so far.
Nothing here predicts: the probabilities come from the models, and the projection is as good as
they are.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from app.prediction.outputs import ModelName
from app.services.predictions import SeasonReview
from app.services.teams import StandingRow

RECENT_DAYS = 7  # "the latest week": the matches of the seven days up to the last one played
SIMULATIONS = 10_000  # enough for every chance to be within about one point of its value
SEED = 2025  # the projection is the same every time it is asked
TOP_PLACES = 4  # the Champions League places (with its qualifying round in Ligue 1)
BOTTOM_PLACES = 3  # relegation (in Bundesliga and Ligue 1 the third from last plays a play-off)


@dataclass(frozen=True, slots=True)
class ModelRecord:
    """One model's hits so far: over the season and over its latest week."""

    model: ModelName
    hits: int
    matches: int
    recent_hits: int
    recent_matches: int


@dataclass(frozen=True, slots=True)
class TrackRecord:
    season: str
    last_day: date | None  # the last day with a reviewed match
    recent_from: date | None  # the first day of the latest week
    models: tuple[ModelRecord, ...]


def track_record(
    season: str, reviews: Mapping[ModelName, SeasonReview], recent_days: int = RECENT_DAYS
) -> TrackRecord:
    """Every model's hits in ``reviews`` (one review per model, of the same season), in all and
    over the ``recent_days`` up to the season's last reviewed match."""
    days = [match.forecast.match_date for review in reviews.values() for match in review.matches]
    last_day = max(days) if days else None
    recent_from = last_day - timedelta(days=recent_days - 1) if last_day else None
    records = []
    for model, review in reviews.items():
        recent = [m for m in review.matches if recent_from and m.forecast.match_date >= recent_from]
        records.append(
            ModelRecord(
                model=model,
                hits=review.hits,
                matches=len(review.matches),
                recent_hits=sum(match.hit for match in recent),
                recent_matches=len(recent),
            )
        )
    return TrackRecord(season, last_day, recent_from, tuple(records))


@dataclass(frozen=True, slots=True)
class Fixture:
    """A match still to be played, with the model's (home win, draw, away win)."""

    home_team: str
    away_team: str
    probabilities: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class ProjectedTeam:
    team: str
    position: int  # in the table today
    played: int
    points: int
    goal_difference: int
    remaining: int  # matches still to play
    expected_points: float
    places: tuple[float, ...]  # the chance of finishing in each place, first to last
    top: float  # the chance of a place among the first TOP_PLACES
    bottom: float  # the chance of a place among the last BOTTOM_PLACES


@dataclass(frozen=True, slots=True)
class Projection:
    simulations: int
    fixtures: int
    teams: tuple[ProjectedTeam, ...]  # by expected points, then today's order


def _check_fixture(fixture: Fixture, teams: set[str]) -> None:
    if fixture.home_team not in teams or fixture.away_team not in teams:
        raise ValueError(f"unknown team in {fixture.home_team} v {fixture.away_team}")
    values = fixture.probabilities
    if any(value < 0 for value in values) or abs(sum(values) - 1) > 1e-9:
        raise ValueError(f"probabilities of {fixture.home_team} v {fixture.away_team}: {values}")


def project_table(
    table: Sequence[StandingRow],
    fixtures: Sequence[Fixture],
    *,
    simulations: int = SIMULATIONS,
    rng: np.random.Generator | None = None,
) -> Projection:
    """Play ``fixtures`` ``simulations`` times from today's ``table``; ``rng`` defaults to a
    generator seeded with ``SEED``.

    Returns every club's expected points and its chance of each final place. Time and memory
    grow as simulations × (fixtures + clubs).
    """
    if not table:
        raise ValueError("the table is empty")
    if simulations < 1:
        raise ValueError(f"simulations must be at least 1, not {simulations}")
    rng = rng if rng is not None else np.random.default_rng(SEED)
    names = [row.team for row in table]
    index = {team: position for position, team in enumerate(names)}
    for fixture in fixtures:
        _check_fixture(fixture, set(index))

    points = np.tile(
        np.array([row.record.points for row in table], dtype=np.int64), (simulations, 1)
    )
    remaining = np.zeros(len(table), dtype=np.int64)
    if fixtures:
        probabilities = np.array([fixture.probabilities for fixture in fixtures])
        draws = rng.random((simulations, len(fixtures)))
        home_win = draws < probabilities[:, 0]
        draw = ~home_win & (draws < probabilities[:, 0] + probabilities[:, 1])
        away_win = ~home_win & ~draw
        for column, fixture in enumerate(fixtures):
            home, away = index[fixture.home_team], index[fixture.away_team]
            points[:, home] += 3 * home_win[:, column] + draw[:, column]
            points[:, away] += 3 * away_win[:, column] + draw[:, column]
            remaining[[home, away]] += 1

    # Today's order (goal difference, goals, name) breaks ties on points: a stable sort keeps it
    finishing = np.argsort(-points, axis=1, kind="stable")  # [simulation, place] -> club
    places = np.zeros((len(table), len(table)))
    for place in range(len(table)):
        places[:, place] = np.bincount(finishing[:, place], minlength=len(table)) / simulations
    expected = points.mean(axis=0)

    bottom_from = max(len(table) - BOTTOM_PLACES, 0)
    teams = [
        ProjectedTeam(
            team=row.team,
            position=row.position,
            played=row.record.played,
            points=row.record.points,
            goal_difference=row.record.goal_difference,
            remaining=int(remaining[club]),
            expected_points=float(expected[club]),
            places=tuple(float(value) for value in places[club]),
            top=float(places[club, :TOP_PLACES].sum()),
            bottom=float(places[club, bottom_from:].sum()),
        )
        for club, row in enumerate(table)
    ]
    teams.sort(key=lambda team: (-team.expected_points, team.position))
    return Projection(simulations, len(fixtures), tuple(teams))
