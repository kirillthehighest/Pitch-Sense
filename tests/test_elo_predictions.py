import math
from dataclasses import replace
from datetime import date

import pytest

from app.data.models import Match, Outcome
from app.prediction.elo_predictions import run_elo
from app.prediction.settings import EloSettings, settings_for


def make(day: date, home_team: str, away_team: str, home_goals: int, away_goals: int) -> Match:
    return Match(
        competition="SP1",
        season="2006-07",
        match_date=day,
        home_team=home_team,
        away_team=away_team,
        home_goals=home_goals,
        away_goals=away_goals,
        result=Outcome.from_score(home_goals, away_goals),
    )


def numbers(prediction) -> tuple[float, float, float]:
    return prediction.home_rating, prediction.away_rating, prediction.expected_home_score


def test_every_match_is_predicted_in_chronological_order(season_matches):
    run = run_elo(reversed(season_matches), EloSettings(20, 0))

    assert [p.match for p in run.predictions] == season_matches


def test_the_first_match_starts_from_equal_ratings(season_matches):
    without_home_advantage = run_elo(season_matches, EloSettings(20, 0))
    with_home_advantage = run_elo(season_matches, EloSettings(20, 100))

    assert numbers(without_home_advantage.predictions[0]) == (1500, 1500, 0.5)
    assert with_home_advantage.predictions[0].expected_home_score == pytest.approx(
        0.640065, abs=1e-6
    )


def test_predictions_use_the_ratings_from_before_the_match_day(season_matches):
    run = run_elo(season_matches, EloSettings(20, 0))

    # Day 1: Alpha lost 0-1 at home to Bravo, so Alpha has 1490 when it hosts Charlie on day 2.
    home_rating, away_rating, expected = numbers(run.predictions[1])
    assert (home_rating, away_rating) == (1490, 1500)
    assert expected == pytest.approx(0.485613, abs=1e-6)


def test_all_matches_of_a_day_are_predicted_before_any_result_is_applied():
    same_day = date(2006, 9, 1)
    # A team never plays twice on one day in real data; here it shows the order of the steps.
    matches = [make(same_day, "A", "B", 3, 0), make(same_day, "C", "A", 0, 0)]

    run = run_elo(matches, EloSettings(20, 0))

    assert [numbers(p) for p in run.predictions] == [(1500, 1500, 0.5), (1500, 1500, 0.5)]


def test_a_promoted_team_starts_at_the_rating_of_the_team_it_replaced(
    season_matches, next_season_matches
):
    renamed = [
        replace(
            match,
            home_team="Echo" if match.home_team == "Delta" else match.home_team,
            away_team="Echo" if match.away_team == "Delta" else match.away_team,
        )
        for match in next_season_matches
    ]
    first_season = run_elo(season_matches, EloSettings(20, 0))

    run = run_elo([*season_matches, *renamed], EloSettings(20, 0))

    echo_first = next(
        p for p in run.predictions if "Echo" in (p.match.home_team, p.match.away_team)
    )
    echo_rating = (
        echo_first.home_rating if echo_first.match.home_team == "Echo" else echo_first.away_rating
    )
    assert echo_rating == first_season.final_ratings["Delta"]
    assert "Delta" not in run.final_ratings


def test_final_ratings_keep_the_league_total(season_matches, next_season_matches):
    run = run_elo([*season_matches, *next_season_matches], EloSettings(30, 80))

    assert math.fsum(run.final_ratings.values()) == pytest.approx(4 * 1500, abs=1e-9)


def test_changing_a_result_never_changes_predictions_on_or_before_its_day(season_matches):
    target = season_matches[6]  # 7 September 2006, the 7th day of the fixture season
    changed = replace(target, home_goals=target.away_goals + 2, result=Outcome.HOME_WIN)
    original_run = run_elo(season_matches, EloSettings(20, 50))

    changed_run = run_elo([*season_matches[:6], changed, *season_matches[7:]], EloSettings(20, 50))

    original = [numbers(p) for p in original_run.predictions]
    after_change = [numbers(p) for p in changed_run.predictions]
    assert original[:7] == after_change[:7]
    assert original[7:] != after_change[7:]


def test_only_one_competition_at_a_time(season_matches):
    with pytest.raises(ValueError, match="one competition"):
        run_elo([*season_matches, replace(season_matches[0], competition="E0")], EloSettings(20, 0))
    with pytest.raises(ValueError, match="at least one match"):
        run_elo([], EloSettings(20, 0))


def test_each_league_is_rated_with_its_own_settings(season_matches):
    premier_league = [replace(m, competition="E0") for m in season_matches]

    la_liga_run, premier_league_run = run_elo(season_matches), run_elo(premier_league)

    la_liga, english = EloSettings(10, 80, goal_margin=True), EloSettings(15, 80, goal_margin=True)
    assert settings_for("SP1").elo == la_liga and settings_for("E0").elo == english
    assert la_liga_run.final_ratings == run_elo(season_matches, la_liga).final_ratings
    assert premier_league_run.final_ratings == run_elo(premier_league, english).final_ratings
    assert la_liga_run.final_ratings != premier_league_run.final_ratings
