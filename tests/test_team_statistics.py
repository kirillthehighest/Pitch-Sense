from dataclasses import replace
from datetime import date

import pytest

from app.data.models import Match, MatchStatistics, Outcome
from app.statistics.team_statistics import (
    MatchHistory,
    TeamResult,
    Venue,
    league_averages,
    recent_form,
    team_match_statistics,
    team_result,
    team_statistics,
)

W, D, L = TeamResult.WIN, TeamResult.DRAW, TeamResult.LOSS


def play(
    day: date,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    season: str = "2006-07",
    statistics: MatchStatistics | None = None,
) -> Match:
    return Match(
        competition="SP1",
        season=season,
        match_date=day,
        home_team=home_team,
        away_team=away_team,
        home_goals=home_goals,
        away_goals=away_goals,
        result=Outcome.from_score(home_goals, away_goals),
        statistics=statistics,
    )


# Alpha in 2006-07: home win 2-0, away draw 1-1, home loss 0-1, away win 3-0.
# Then a home win 1-0 in 2007-08.
ALPHA_MATCHES = (
    play(date(2006, 9, 1), "Alpha", "Bravo", 2, 0),
    play(date(2006, 9, 8), "Charlie", "Alpha", 1, 1),
    play(date(2006, 9, 15), "Alpha", "Charlie", 0, 1),
    play(date(2006, 9, 22), "Bravo", "Alpha", 0, 3),
    play(date(2007, 9, 1), "Alpha", "Bravo", 1, 0, season="2007-08"),
)
END_OF_FIRST_SEASON = date(2007, 6, 30)
AFTER_FIRST_MATCH_OF_SECOND_SEASON = date(2007, 9, 2)

# Field order: shots, shots on target, fouls, corners, yellow and red cards; home then away.
ALPHA_AT_HOME_STATISTICS = MatchStatistics(10, 4, 5, 1, 12, 15, 6, 2, 1, 3, 0, 1)
ALPHA_AWAY_STATISTICS = MatchStatistics(8, 6, 3, 2, 10, 9, 4, 5, 2, 1, 1, 0)
STATISTICS_MATCHES = (
    play(date(2006, 9, 1), "Alpha", "Bravo", 2, 0, statistics=ALPHA_AT_HOME_STATISTICS),
    play(date(2006, 9, 8), "Charlie", "Alpha", 1, 1, statistics=ALPHA_AWAY_STATISTICS),
    play(date(2006, 9, 15), "Alpha", "Charlie", 0, 1),  # no statistics recorded
)

TEAM_SELECTIONS = [
    {},
    {"venue": Venue.HOME},
    {"venue": Venue.AWAY},
    {"last": 3},
    {"season": "2006-07"},
]
LEAGUE_SELECTIONS = [{}, {"last": 3}, {"season": "2006-07"}]


@pytest.fixture
def history() -> MatchHistory:
    return MatchHistory(ALPHA_MATCHES)


# --- history ---


def test_history_knows_its_competition_and_teams(history):
    assert history.competition == "SP1"
    assert history.teams == ["Alpha", "Bravo", "Charlie"]


def test_history_needs_matches_of_a_single_competition():
    with pytest.raises(ValueError, match="at least one match"):
        MatchHistory([])
    with pytest.raises(ValueError, match="one competition"):
        MatchHistory([*ALPHA_MATCHES, replace(ALPHA_MATCHES[0], competition="E0")])


def test_input_order_does_not_matter():
    shuffled = MatchHistory(reversed(ALPHA_MATCHES))
    ordered = MatchHistory(ALPHA_MATCHES)

    assert team_statistics(shuffled, "Alpha", END_OF_FIRST_SEASON) == team_statistics(
        ordered, "Alpha", END_OF_FIRST_SEASON
    )


# --- results and records ---


def test_team_result_from_each_side():
    home_win, draw = ALPHA_MATCHES[0], ALPHA_MATCHES[1]

    assert team_result(home_win, "Alpha") is W
    assert team_result(home_win, "Bravo") is L
    assert team_result(draw, "Alpha") is D
    assert team_result(draw, "Charlie") is D
    with pytest.raises(ValueError, match="did not play"):
        team_result(home_win, "Charlie")


def test_record_over_all_matches_before_a_date(history):
    statistics = team_statistics(history, "Alpha", END_OF_FIRST_SEASON)

    assert (statistics.played, statistics.wins, statistics.draws, statistics.losses) == (4, 2, 1, 1)
    assert (statistics.goals_for, statistics.goals_against) == (6, 2)
    assert (statistics.points, statistics.goal_difference) == (7, 4)
    assert statistics.points_per_match == 1.75
    assert statistics.win_rate == 0.5
    assert statistics.goals_for_per_match == 1.5
    assert statistics.goals_against_per_match == 0.5


def test_the_match_on_the_query_date_is_excluded(history):
    statistics = team_statistics(history, "Alpha", date(2006, 9, 15))

    assert (statistics.played, statistics.points) == (2, 4)


def test_other_matches_on_the_same_day_are_excluded():
    same_day = date(2006, 9, 1)
    history = MatchHistory(
        [play(same_day, "Alpha", "Bravo", 1, 0), play(same_day, "Charlie", "Delta", 2, 2)]
    )

    assert team_statistics(history, "Charlie", same_day).played == 0
    assert team_statistics(history, "Charlie", date(2006, 9, 2)).played == 1
    assert league_averages(history, same_day).matches == 0


def test_home_and_away_records(history):
    home = team_statistics(history, "Alpha", END_OF_FIRST_SEASON, venue=Venue.HOME)
    away = team_statistics(history, "Alpha", END_OF_FIRST_SEASON, venue=Venue.AWAY)

    assert (home.played, home.points, home.goals_for, home.goals_against) == (2, 3, 2, 1)
    assert (away.played, away.points, away.goals_for, away.goals_against) == (2, 4, 4, 1)


def test_last_n_matches(history):
    statistics = team_statistics(history, "Alpha", END_OF_FIRST_SEASON, last=2)

    assert (statistics.played, statistics.points) == (2, 3)
    assert (statistics.goals_for, statistics.goals_against) == (3, 1)


def test_last_n_home_matches(history):
    statistics = team_statistics(history, "Alpha", END_OF_FIRST_SEASON, last=1, venue=Venue.HOME)

    assert (statistics.played, statistics.losses) == (1, 1)


def test_season_selection(history):
    def played(season):
        return team_statistics(
            history, "Alpha", AFTER_FIRST_MATCH_OF_SECOND_SEASON, season=season
        ).played

    assert played("2007-08") == 1
    assert played("2006-07") == 4
    assert played(None) == 5


def test_team_without_earlier_matches_has_no_rates(history):
    statistics = team_statistics(history, "Charlie", date(2006, 9, 1))

    assert (statistics.played, statistics.points) == (0, 0)
    assert statistics.points_per_match is None
    assert statistics.win_rate is None
    assert statistics.goals_for_per_match is None
    assert recent_form(history, "Charlie", date(2006, 9, 1)) == []


def test_unknown_team_is_rejected(history):
    with pytest.raises(ValueError, match="unknown team"):
        team_statistics(history, "Zulu", END_OF_FIRST_SEASON)


def test_selection_sizes_must_be_positive(history):
    with pytest.raises(ValueError, match="last"):
        team_statistics(history, "Alpha", END_OF_FIRST_SEASON, last=0)
    with pytest.raises(ValueError, match="last"):
        league_averages(history, END_OF_FIRST_SEASON, last=0)
    with pytest.raises(ValueError, match="length"):
        recent_form(history, "Alpha", END_OF_FIRST_SEASON, length=0)


def test_season_totals_are_consistent(season_matches):
    history = MatchHistory(season_matches)
    records = [team_statistics(history, team, date(2006, 9, 13)) for team in history.teams]
    draws = sum(match.result is Outcome.DRAW for match in season_matches)
    decisive = len(season_matches) - draws

    assert all(record.played == 6 for record in records)
    assert sum(record.points for record in records) == 3 * decisive + 2 * draws
    assert sum(record.wins for record in records) == sum(record.losses for record in records)
    assert sum(record.goals_for for record in records) == sum(
        record.goals_against for record in records
    )


# --- form ---


def test_recent_form_is_oldest_first(history):
    assert recent_form(history, "Alpha", END_OF_FIRST_SEASON, length=3) == [D, L, W]
    assert recent_form(history, "Alpha", AFTER_FIRST_MATCH_OF_SECOND_SEASON) == [W, D, L, W, W]


def test_last_n_matches_cross_the_season_boundary(history):
    assert recent_form(history, "Alpha", AFTER_FIRST_MATCH_OF_SECOND_SEASON, length=3) == [L, W, W]


# --- match statistics ---


def test_match_statistics_average_own_and_opponent_values():
    averages = team_match_statistics(MatchHistory(STATISTICS_MATCHES), "Alpha", END_OF_FIRST_SEASON)

    assert averages.matches_with_statistics == 2
    assert (averages.shots, averages.opponent_shots) == (8.0, 6.0)
    assert (averages.shots_on_target, averages.opponent_shots_on_target) == (3.5, 2.0)
    assert (averages.fouls, averages.opponent_fouls) == (10.5, 12.5)
    assert (averages.corners, averages.opponent_corners) == (5.5, 3.0)
    assert (averages.yellow_cards, averages.opponent_yellow_cards) == (1.0, 2.5)
    assert (averages.red_cards, averages.opponent_red_cards) == (0.0, 1.0)


def test_match_statistics_follow_the_venue_selection():
    averages = team_match_statistics(
        MatchHistory(STATISTICS_MATCHES), "Alpha", END_OF_FIRST_SEASON, venue=Venue.HOME
    )

    assert averages.matches_with_statistics == 1
    assert (averages.shots, averages.opponent_shots) == (10.0, 4.0)


def test_match_statistics_are_empty_without_recorded_statistics(history):
    averages = team_match_statistics(history, "Alpha", END_OF_FIRST_SEASON)

    assert averages.matches_with_statistics == 0
    assert averages.shots is None
    assert averages.opponent_red_cards is None


# --- league averages ---


def test_league_averages_over_all_earlier_matches(history):
    averages = league_averages(history, END_OF_FIRST_SEASON)

    assert averages.matches == 4
    assert (averages.home_goals_per_match, averages.away_goals_per_match) == (0.75, 1.25)
    assert (averages.home_win_rate, averages.draw_rate, averages.away_win_rate) == (
        0.25,
        0.25,
        0.5,
    )


def test_league_averages_by_season_and_by_last_matches(history):
    this_season = league_averages(history, AFTER_FIRST_MATCH_OF_SECOND_SEASON, season="2007-08")
    last_two = league_averages(history, END_OF_FIRST_SEASON, last=2)

    assert (this_season.matches, this_season.home_goals_per_match) == (1, 1.0)
    assert (this_season.home_win_rate, this_season.draw_rate) == (1.0, 0.0)
    assert (last_two.home_goals_per_match, last_two.away_goals_per_match) == (0.0, 2.0)
    assert last_two.away_win_rate == 1.0


def test_league_averages_exclude_the_query_date(history):
    averages = league_averages(history, date(2006, 9, 15))

    assert averages.matches == 2
    assert (averages.home_goals_per_match, averages.away_goals_per_match) == (1.5, 0.5)


def test_league_averages_without_matches_are_empty(history):
    averages = league_averages(history, date(2006, 9, 1))

    assert averages.matches == 0
    assert averages.home_goals_per_match is None
    assert averages.home_win_rate is None


def test_outcome_frequencies_sum_to_one(season_matches):
    averages = league_averages(MatchHistory(season_matches), date(2006, 9, 13))

    assert averages.home_win_rate + averages.draw_rate + averages.away_win_rate == pytest.approx(1)


# --- data leakage ---


def changed_on_seventh_of_september(season_matches: list[Match]) -> tuple[Match, list[Match]]:
    """Return the 7 Sept 2006 match and the season with its result and statistics changed."""
    target = season_matches[6]
    changed = replace(
        target,
        home_goals=target.away_goals + 2,
        result=Outcome.HOME_WIN,
        statistics=MatchStatistics(*[9] * 12),
    )
    assert (changed.result, changed.statistics) != (target.result, target.statistics)
    return target, [*season_matches[:6], changed, *season_matches[7:]]


@pytest.mark.parametrize("selection", TEAM_SELECTIONS)
def test_changing_a_match_never_changes_team_values_on_or_before_its_day(season_matches, selection):
    target, changed_season = changed_on_seventh_of_september(season_matches)
    original, changed = MatchHistory(season_matches), MatchHistory(changed_season)
    form_selection = {
        ("length" if key == "last" else key): value for key, value in selection.items()
    }

    for team in original.teams:
        for day in range(1, 8):  # up to and including the day of the changed match
            before = date(2006, 9, day)
            assert team_statistics(original, team, before, **selection) == team_statistics(
                changed, team, before, **selection
            )
            assert team_match_statistics(
                original, team, before, **selection
            ) == team_match_statistics(changed, team, before, **selection)
            assert recent_form(original, team, before, **form_selection) == recent_form(
                changed, team, before, **form_selection
            )

    the_day_after = date(2006, 9, 8)
    assert team_statistics(original, target.home_team, the_day_after) != team_statistics(
        changed, target.home_team, the_day_after
    )
    assert team_match_statistics(
        original, target.home_team, the_day_after
    ) != team_match_statistics(changed, target.home_team, the_day_after)


@pytest.mark.parametrize("selection", LEAGUE_SELECTIONS)
def test_changing_a_match_never_changes_league_values_on_or_before_its_day(
    season_matches, selection
):
    _, changed_season = changed_on_seventh_of_september(season_matches)
    original, changed = MatchHistory(season_matches), MatchHistory(changed_season)

    for day in range(1, 8):
        before = date(2006, 9, day)
        assert league_averages(original, before, **selection) == league_averages(
            changed, before, **selection
        )

    the_day_after = date(2006, 9, 8)
    assert league_averages(original, the_day_after) != league_averages(changed, the_day_after)
