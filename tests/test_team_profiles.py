from dataclasses import replace

import pytest

from app.data.models import Outcome
from app.statistics.team_profiles import PROFILE_FEATURES, season_profiles, seasons_in
from app.statistics.team_statistics import MatchHistory


def test_hand_computed_profile(season_matches):
    alpha = season_profiles(MatchHistory(season_matches), "2006-07")[0]

    # Alpha at home: 0-1, 1-0, 2-1; away: 0-0, 1-0 (win at Charlie), 0-0.
    # Goals 4 for and 2 against in 6 matches; 6 points at home and 5 away (11 in total).
    # Every statistic of fixture match number m is m % 5, so Alpha's shots on target are
    # 0 + 1 + 2 at home and 3 + 1 + 4 away: 11, and the same against.
    assert (alpha.team, alpha.season, alpha.matches) == ("Alpha", "2006-07", 6)
    assert alpha.values == pytest.approx((4 / 6, 2 / 6, 11 / 6, 11 / 6, 11 / 6, 6 / 3 - 5 / 3))


def test_every_team_of_the_season_gets_a_profile(season_matches):
    profiles = season_profiles(MatchHistory(season_matches), "2006-07")

    assert [p.team for p in profiles] == ["Alpha", "Bravo", "Charlie", "Delta"]
    assert all(len(p.values) == len(PROFILE_FEATURES) == 6 for p in profiles)


def test_a_profile_uses_only_its_own_season(season_matches, next_season_matches):
    flipped_next_season = [
        replace(
            m,
            home_goals=m.away_goals,
            away_goals=m.home_goals,
            result=Outcome.from_score(m.away_goals, m.home_goals),
        )
        for m in next_season_matches
    ]

    alone = season_profiles(MatchHistory(season_matches), "2006-07")
    with_next = season_profiles(MatchHistory([*season_matches, *flipped_next_season]), "2006-07")

    assert alone == with_next


def test_seasons_are_listed_in_order(season_matches, next_season_matches):
    history = MatchHistory([*next_season_matches, *season_matches])

    assert seasons_in(history) == ["2006-07", "2007-08"]


def test_a_profile_needs_shot_statistics(season_matches):
    without_statistics = [replace(m, statistics=None) for m in season_matches]

    with pytest.raises(ValueError, match="no shot statistics"):
        season_profiles(MatchHistory(without_statistics), "2006-07")


def test_an_unknown_season_is_rejected(season_matches):
    with pytest.raises(ValueError, match="no matches"):
        season_profiles(MatchHistory(season_matches), "1999-00")
