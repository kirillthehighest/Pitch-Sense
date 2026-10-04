from dataclasses import replace

import pytest

from app.data.models import Outcome
from app.evaluation.team_clustering import (
    cluster_profiles,
    descriptive_clusters,
    point_in_time_groups,
)
from app.statistics.team_profiles import season_profiles
from app.statistics.team_statistics import MatchHistory


@pytest.fixture
def three_seasons(season_matches, next_season_matches):
    """2006-07 and 2007-08 as in the fixtures; in 2008-09 Echo replaces Delta (promotion)."""
    third = [
        replace(
            m,
            season="2008-09",
            match_date=m.match_date.replace(year=2008),
            home_team="Echo" if m.home_team == "Delta" else m.home_team,
            away_team="Echo" if m.away_team == "Delta" else m.away_team,
        )
        for m in season_matches
    ]
    return [*season_matches, *next_season_matches, *third]


def test_descriptive_clusters_cover_every_team_season(three_seasons):
    clusters = descriptive_clusters(MatchHistory(three_seasons), ["2006-07", "2007-08"], k=2)

    assert clusters.k == 2
    assert len(clusters.profiles) == len(clusters.result.labels) == 8
    assert {p.season for p in clusters.profiles} == {"2006-07", "2007-08"}


def test_cluster_of_places_a_profile_at_its_nearest_centre(season_matches):
    profiles = season_profiles(MatchHistory(season_matches), "2006-07")
    clusters = cluster_profiles(profiles, k=2)

    assert [clusters.cluster_of(p) for p in profiles] == clusters.result.labels.tolist()


def test_point_in_time_groups_mark_promoted_teams(three_seasons):
    groups = point_in_time_groups(MatchHistory(three_seasons), "2008-09", k=2)

    assert sorted(groups) == ["Alpha", "Bravo", "Charlie", "Echo"]
    assert groups["Echo"] is None
    assert all(isinstance(groups[team], int) for team in ("Alpha", "Bravo", "Charlie"))


def test_point_in_time_groups_use_the_previous_season_profiles(three_seasons):
    history = MatchHistory(three_seasons)
    clusters = descriptive_clusters(history, ["2006-07", "2007-08"], k=2)
    previous = {p.team: p for p in season_profiles(history, "2007-08")}

    groups = point_in_time_groups(history, "2008-09", k=2)

    for team in ("Alpha", "Bravo", "Charlie"):
        assert groups[team] == clusters.group_of(previous[team])


def test_results_of_the_season_itself_never_change_its_groups(three_seasons):
    flipped = [
        replace(
            m,
            home_goals=m.away_goals,
            away_goals=m.home_goals,
            result=Outcome.from_score(m.away_goals, m.home_goals),
        )
        if m.season == "2008-09"
        else m
        for m in three_seasons
    ]

    original = point_in_time_groups(MatchHistory(three_seasons), "2008-09", k=2)
    after_change = point_in_time_groups(MatchHistory(flipped), "2008-09", k=2)

    assert original == after_change


def test_the_first_season_has_no_earlier_season(three_seasons):
    with pytest.raises(ValueError, match="no completed season before"):
        point_in_time_groups(MatchHistory(three_seasons), "2006-07", k=2)
    with pytest.raises(ValueError, match="no matches"):
        point_in_time_groups(MatchHistory(three_seasons), "1999-00", k=2)


def test_groups_are_ranked_by_points_per_match(season_matches):
    profiles = season_profiles(MatchHistory(season_matches), "2006-07")
    clusters = cluster_profiles(profiles, k=2)

    best = max(profiles, key=lambda profile: profile.values[4])
    worst = min(profiles, key=lambda profile: profile.values[4])
    assert clusters.group_of(best) == 0
    assert clusters.group_of(worst) == 1
    assert sorted(set(clusters.groups)) == [0, 1]


def test_cluster_profiles_needs_profiles():
    with pytest.raises(ValueError):
        cluster_profiles([], k=2)
