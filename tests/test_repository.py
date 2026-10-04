import sqlite3
from datetime import date, time

import pytest

from app.data.models import Match, MatchStatistics, Outcome
from app.data.repository import MatchRepository

STATISTICS = MatchStatistics(*range(1, 13))


@pytest.fixture
def repository():
    with MatchRepository(sqlite3.connect(":memory:")) as repository:
        yield repository


def make_match(
    match_date: date,
    home_team: str = "Sevilla",
    away_team: str = "Betis",
    competition: str = "SP1",
    season: str = "2006-07",
    kickoff_time: time | None = None,
    statistics: MatchStatistics | None = None,
) -> Match:
    return Match(
        competition=competition,
        season=season,
        match_date=match_date,
        home_team=home_team,
        away_team=away_team,
        home_goals=2,
        away_goals=1,
        result=Outcome.HOME_WIN,
        kickoff_time=kickoff_time,
        statistics=statistics,
    )


def test_stored_matches_read_back_unchanged(repository):
    with_everything = make_match(date(2020, 9, 12), kickoff_time=time(21, 0), statistics=STATISTICS)
    without_optional_fields = make_match(date(2020, 9, 13), "Getafe", "Osasuna")

    repository.replace_competition("SP1", [with_everything, without_optional_fields])

    assert repository.matches("SP1") == [with_everything, without_optional_fields]


def test_matches_are_returned_in_chronological_order(repository):
    first = make_match(date(2006, 8, 26), "Valencia", "Betis")
    second = make_match(date(2006, 8, 27), "Sevilla", "Getafe")
    third = make_match(date(2006, 9, 9), "Betis", "Sevilla")

    repository.replace_competition("SP1", [third, first, second])

    assert repository.matches("SP1") == [first, second, third]


def test_matches_can_be_filtered_by_season(repository):
    earlier = make_match(date(2006, 9, 9))
    later = make_match(date(2007, 9, 9), season="2007-08")
    repository.replace_competition("SP1", [earlier, later])

    assert repository.matches("SP1", season="2007-08") == [later]


def test_replacing_a_competition_keeps_other_competitions(repository):
    old_spanish = make_match(date(2006, 9, 9))
    english = make_match(date(2006, 9, 9), "Arsenal", "Chelsea", competition="E0")
    new_spanish = make_match(date(2006, 9, 10), "Getafe", "Osasuna")
    repository.replace_competition("SP1", [old_spanish])
    repository.replace_competition("E0", [english])

    stored = repository.replace_competition("SP1", [new_spanish])

    assert stored == 1
    assert repository.matches("SP1") == [new_spanish]
    assert repository.matches("E0") == [english]


def test_failed_replacement_keeps_the_previous_data(repository):
    original = make_match(date(2006, 9, 9))
    duplicate = make_match(date(2006, 9, 10), "Getafe", "Osasuna")
    repository.replace_competition("SP1", [original])

    with pytest.raises(sqlite3.IntegrityError):
        repository.replace_competition("SP1", [duplicate, duplicate])

    assert repository.matches("SP1") == [original]


def test_matches_from_another_competition_are_rejected(repository):
    english = make_match(date(2006, 9, 9), "Arsenal", "Chelsea", competition="E0")

    with pytest.raises(ValueError, match="belong to E0, not SP1"):
        repository.replace_competition("SP1", [english])

    assert repository.competitions() == []


def test_competitions_seasons_and_teams_are_listed_sorted(repository):
    repository.replace_competition(
        "SP1",
        [
            make_match(date(2007, 9, 9), "Valencia", "Betis", season="2007-08"),
            make_match(date(2006, 9, 9), "Sevilla", "Getafe"),
        ],
    )
    repository.replace_competition("E0", [make_match(date(2006, 9, 9), "Arsenal", "Chelsea", "E0")])

    assert repository.competitions() == ["E0", "SP1"]
    assert repository.seasons("SP1") == ["2006-07", "2007-08"]
    assert repository.teams("SP1") == ["Betis", "Getafe", "Sevilla", "Valencia"]
    assert repository.teams("SP1", season="2006-07") == ["Getafe", "Sevilla"]


def test_unknown_competition_has_no_data(repository):
    assert repository.matches("XX") == []
    assert repository.seasons("XX") == []
    assert repository.teams("XX") == []


def test_database_file_keeps_matches_between_connections(tmp_path):
    match = make_match(date(2006, 9, 9), statistics=STATISTICS)
    path = tmp_path / "pitchsense.db"
    with MatchRepository.open(path) as repository:
        repository.replace_competition("SP1", [match])

    with MatchRepository.open(path) as reopened:
        assert reopened.matches("SP1") == [match]
