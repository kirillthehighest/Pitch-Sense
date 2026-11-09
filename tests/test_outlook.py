"""The season at a glance (Phase 25): the projected final table."""

from datetime import date

import numpy as np
import pytest

from app.services.outlook import (
    BOTTOM_PLACES,
    TOP_PLACES,
    Fixture,
    project_table,
)
from app.services.teams import StandingRow
from app.statistics.team_statistics import TeamStatistics


def row(
    position: int, team: str, points: int, played: int = 10, difference: int = 0
) -> StandingRow:
    record = TeamStatistics(
        team=team,
        before=date(2026, 11, 1),
        played=played,
        wins=points // 3,
        draws=points % 3,
        losses=played - points // 3 - points % 3,
        goals_for=10 + max(difference, 0),
        goals_against=10 - min(difference, 0),
    )
    return StandingRow(position=position, team=team, record=record)


# --- project_table ---

TABLE = [row(1, "Alpha", 30), row(2, "Bravo", 20), row(3, "Charlie", 12), row(4, "Delta", 5)]


def test_without_fixtures_the_table_is_final():
    found = project_table(TABLE, [], simulations=50)

    assert [team.team for team in found.teams] == ["Alpha", "Bravo", "Charlie", "Delta"]
    for place, team in enumerate(found.teams):
        assert team.places[place] == 1.0 and team.expected_points == team.points


def test_certain_results_give_certain_points():
    fixtures = [
        Fixture("Delta", "Alpha", (1.0, 0.0, 0.0)),
        Fixture("Charlie", "Bravo", (0.0, 1.0, 0.0)),
    ]

    found = {team.team: team for team in project_table(TABLE, fixtures, simulations=20).teams}

    assert found["Delta"].expected_points == 8 and found["Alpha"].expected_points == 30
    assert found["Charlie"].expected_points == 13 and found["Bravo"].expected_points == 21
    assert found["Alpha"].remaining == found["Delta"].remaining == 1


def test_every_club_finishes_somewhere_and_every_place_is_taken():
    fixtures = [
        Fixture(home, away, (0.45, 0.27, 0.28))
        for home in ("Alpha", "Bravo", "Charlie", "Delta")
        for away in ("Alpha", "Bravo", "Charlie", "Delta")
        if home != away
    ]

    found = project_table(TABLE, fixtures, simulations=2000)

    places = np.array([team.places for team in found.teams])
    assert np.allclose(places.sum(axis=1), 1.0) and np.allclose(places.sum(axis=0), 1.0)
    for team in found.teams:
        assert team.top == pytest.approx(sum(team.places[:TOP_PLACES]))
        assert team.bottom == pytest.approx(sum(team.places[-BOTTOM_PLACES:]))


def test_expected_points_approach_the_sum_of_each_matchs_expected_points():
    fixtures = [Fixture("Charlie", "Delta", (0.5, 0.3, 0.2))] * 6

    found = {team.team: team for team in project_table(TABLE, fixtures, simulations=20_000).teams}

    assert found["Charlie"].expected_points == pytest.approx(12 + 6 * (3 * 0.5 + 0.3), abs=0.1)
    assert found["Delta"].expected_points == pytest.approx(5 + 6 * (3 * 0.2 + 0.3), abs=0.1)


def test_ties_on_points_keep_todays_order():
    table = [row(1, "Alpha", 10, difference=5), row(2, "Bravo", 10, difference=1)]

    found = project_table(table, [], simulations=10)

    assert [team.team for team in found.teams] == ["Alpha", "Bravo"]
    assert found.teams[0].places == (1.0, 0.0)


def test_the_same_seed_gives_the_same_projection():
    fixtures = [
        Fixture("Bravo", "Charlie", (0.4, 0.3, 0.3)),
        Fixture("Alpha", "Delta", (0.7, 0.2, 0.1)),
    ]

    first = project_table(TABLE, fixtures, simulations=500, rng=np.random.default_rng(7))
    second = project_table(TABLE, fixtures, simulations=500, rng=np.random.default_rng(7))

    assert first == second


@pytest.mark.parametrize(
    ("fixtures", "simulations", "message"),
    [
        ([Fixture("Alpha", "Zulu", (0.5, 0.3, 0.2))], 10, "unknown team"),
        ([Fixture("Alpha", "Bravo", (0.5, 0.3, 0.3))], 10, "probabilities"),
        ([Fixture("Alpha", "Bravo", (1.2, 0.0, -0.2))], 10, "probabilities"),
        ([], 0, "simulations"),
    ],
)
def test_invalid_input_is_refused(fixtures, simulations, message):
    with pytest.raises(ValueError, match=message):
        project_table(TABLE, fixtures, simulations=simulations)


def test_an_empty_table_is_refused():
    with pytest.raises(ValueError, match="empty"):
        project_table([], [])
