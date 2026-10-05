import pytest

from app.data.competitions import COMPETITIONS, Competition, competition


def test_the_five_leagues():
    names = {code: league.name for code, league in COMPETITIONS.items()}

    assert names == {
        "E0": "Premier League",
        "SP1": "La Liga",
        "I1": "Serie A",
        "D1": "Bundesliga",
        "F1": "Ligue 1",
    }


def test_the_bundesliga_has_18_teams_and_306_matches_a_season():
    bundesliga = competition("D1")

    assert (bundesliga.teams_in("2010-11"), bundesliga.season_length) == (18, 306)
    assert bundesliga.venue_season_length == 17


def test_ligue_1_changed_size_and_stopped_2019_20_early():
    ligue_1 = competition("F1")

    assert [ligue_1.teams_in(season) for season in ("2022-23", "2023-24")] == [20, 18]
    assert ligue_1.stopped_early == {"2019-20": 279}
    assert ligue_1.season_length == 380  # model windows use the usual size


def test_an_unknown_code_is_an_error():
    with pytest.raises(ValueError, match="unknown competition 'XX'"):
        competition("XX")


def test_a_league_needs_two_teams():
    with pytest.raises(ValueError, match="at least two teams"):
        Competition("XX", "Tiny", 1)
