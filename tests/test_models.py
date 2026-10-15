from dataclasses import FrozenInstanceError, replace
from datetime import date, time

import pytest

from app.data.models import Fixture, Match, MatchStatistics, Outcome


def valid_match() -> Match:
    return Match(
        competition="SP1",
        season="2006-07",
        match_date=date(2006, 8, 27),
        home_team="Sevilla",
        away_team="Ath Bilbao",
        home_goals=4,
        away_goals=0,
        result=Outcome.HOME_WIN,
    )


@pytest.mark.parametrize(
    ("home_goals", "away_goals", "expected"),
    [(2, 1, Outcome.HOME_WIN), (1, 1, Outcome.DRAW), (0, 3, Outcome.AWAY_WIN)],
)
def test_outcome_from_score(home_goals, away_goals, expected):
    assert Outcome.from_score(home_goals, away_goals) is expected


def test_valid_match_keeps_its_values():
    match = valid_match()

    assert (match.home_team, match.away_team, match.result) == ("Sevilla", "Ath Bilbao", "H")
    assert match.kickoff_time is None
    assert match.statistics is None


@pytest.mark.parametrize(
    "changes",
    [
        {"home_goals": -1, "result": Outcome.AWAY_WIN},
        {"away_team": "Sevilla"},
        {"home_team": ""},
        {"competition": ""},
        {"result": Outcome.DRAW},
    ],
)
def test_match_rejects_inconsistent_values(changes):
    with pytest.raises(ValueError):
        replace(valid_match(), **changes)


def test_match_is_immutable():
    with pytest.raises(FrozenInstanceError):
        valid_match().home_goals = 5


def test_statistics_reject_negative_values():
    values = dict.fromkeys(
        (
            "home_shots",
            "away_shots",
            "home_shots_on_target",
            "away_shots_on_target",
            "home_fouls",
            "away_fouls",
            "home_corners",
            "away_corners",
            "home_yellow_cards",
            "away_yellow_cards",
            "home_red_cards",
            "away_red_cards",
        ),
        0,
    )
    values["away_corners"] = -2

    with pytest.raises(ValueError, match="away_corners"):
        MatchStatistics(**values)


def test_a_fixture_has_teams_a_date_and_maybe_a_kickoff():
    fixture = Fixture("SP1", "2026-27", date(2026, 10, 17), "Betis", "Barcelona", time(18, 30))

    assert (fixture.home_team, fixture.away_team, fixture.kickoff_time) == (
        "Betis",
        "Barcelona",
        time(18, 30),
    )
    assert Fixture("SP1", "2026-27", date(2026, 10, 17), "A", "B").kickoff_time is None


@pytest.mark.parametrize(
    ("competition", "season", "home_team", "away_team", "message"),
    [
        ("", "2026-27", "A", "B", "competition and season"),
        ("SP1", "", "A", "B", "competition and season"),
        ("SP1", "2026-27", "", "B", "team names"),
        ("SP1", "2026-27", "A", "A", "itself"),
    ],
)
def test_a_fixture_rejects_inconsistent_values(competition, season, home_team, away_team, message):
    with pytest.raises(ValueError, match=message):
        Fixture(competition, season, date(2026, 10, 17), home_team, away_team)
