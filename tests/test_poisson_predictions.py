import math
from dataclasses import replace
from datetime import date

import pytest

from app.data.models import Match, Outcome
from app.prediction.poisson_predictions import predict_match, run_poisson, weighted_record
from app.prediction.settings import PoissonSettings
from app.statistics.team_statistics import MatchHistory, Venue

SETTINGS = PoissonSettings(team_window=19, prior_matches=1, league_window=380)


def make(day: int, home_team: str, away_team: str, home_goals: int, away_goals: int) -> Match:
    return Match(
        competition="SP1",
        season="2006-07",
        match_date=date(2006, 9, day),
        home_team=home_team,
        away_team=away_team,
        home_goals=home_goals,
        away_goals=away_goals,
        result=Outcome.from_score(home_goals, away_goals),
    )


# Before 5 September the league has 6 home goals and 4 away goals in 4 matches: 1.5 and 1.0.
EARLIER = [
    make(1, "A", "B", 2, 1),
    make(2, "C", "D", 1, 1),
    make(3, "B", "C", 0, 2),
    make(4, "D", "A", 3, 0),
]


def numbers(prediction) -> tuple[float, ...]:
    return (
        prediction.home_attack,
        prediction.home_defence_weakness,
        prediction.away_attack,
        prediction.away_defence_weakness,
        prediction.distribution.home_expected_goals,
        prediction.distribution.away_expected_goals,
    )


def test_hand_computed_prediction():
    target = make(5, "A", "C", 1, 1)

    prediction = predict_match(MatchHistory([*EARLIER, target]), target, SETTINGS)

    assert (prediction.league_home_goals, prediction.league_away_goals) == (1.5, 1.0)
    # A at home: scored 2 and conceded 1 in one match. C away: scored 2 and conceded 0.
    assert prediction.home_attack == pytest.approx((2 + 1.5) / 2 / 1.5)  # 1.1667
    assert prediction.home_defence_weakness == pytest.approx((1 + 1.0) / 2 / 1.0)  # 1.0
    assert prediction.away_attack == pytest.approx((2 + 1.0) / 2 / 1.0)  # 1.5
    assert prediction.away_defence_weakness == pytest.approx((0 + 1.5) / 2 / 1.5)  # 0.5
    assert prediction.distribution.home_expected_goals == pytest.approx(0.875)  # 1.1667 * 0.5 * 1.5
    assert prediction.distribution.away_expected_goals == pytest.approx(1.5)  # 1.5 * 1.0 * 1.0


def test_a_team_without_history_is_treated_as_average():
    target = make(5, "E", "A", 0, 0)  # E has never played

    prediction = predict_match(MatchHistory([*EARLIER, target]), target, SETTINGS)

    assert (prediction.home_attack, prediction.home_defence_weakness) == (1.0, 1.0)
    # A away: scored 0 and conceded 3 in one match.
    assert prediction.distribution.home_expected_goals == pytest.approx(1.0 * 1.5 * 1.5)
    assert prediction.distribution.away_expected_goals == pytest.approx(0.5 * 1.0 * 1.0)


def test_only_the_last_team_window_matches_count():
    later_home_match = make(5, "A", "B", 0, 0)
    target = make(6, "A", "C", 1, 1)
    history = MatchHistory([*EARLIER, later_home_match, target])

    prediction = predict_match(history, target, PoissonSettings(1, 1, 380))

    # Only A's 0-0 on 5 September counts; the 2-1 on 1 September is outside the window.
    assert prediction.home_attack == pytest.approx((0 + 1 * 1.2) / 2 / 1.2)


def test_recent_matches_weigh_more_with_a_half_life():
    later_home_match = make(5, "A", "B", 0, 0)
    target = make(6, "A", "C", 1, 1)
    history = MatchHistory([*EARLIER, later_home_match, target])

    prediction = predict_match(history, target, PoissonSettings(19, 1, 380, half_life=1))

    # A's home matches weigh 0.5 (2-1 on 1 September) and 1 (0-0 on 5 September): 1 goal scored
    # in 1.5 weighted matches. The league has 1.2 home goals per match before 6 September.
    assert prediction.home_attack == pytest.approx((1 + 1 * 1.2) / (1.5 + 1) / 1.2)
    record = weighted_record(
        history, "A", target.match_date, last=19, venue=Venue.HOME, half_life=1
    )
    assert (record.goals_for, record.goals_against, record.matches) == (1.0, 0.5, 1.5)


def test_the_settings_rho_reaches_the_score_table():
    target = make(5, "A", "C", 1, 1)
    history = MatchHistory([*EARLIER, target])

    plain = predict_match(history, target, SETTINGS)
    corrected = predict_match(history, target, replace(SETTINGS, rho=-0.1))

    assert numbers(corrected) == numbers(plain)  # the same strengths and expected goals
    assert corrected.distribution.rho == -0.1
    draw = corrected.distribution.outcome_probabilities()[1]
    assert draw > plain.distribution.outcome_probabilities()[1]


def test_no_prediction_without_league_goals():
    target = make(2, "C", "D", 1, 1)
    goalless_first_day = make(1, "A", "B", 0, 0)

    assert predict_match(MatchHistory([target]), target, SETTINGS) is None
    assert predict_match(MatchHistory([goalless_first_day, target]), target, SETTINGS) is None


def test_the_fixture_season_is_predicted_from_its_third_day(season_matches):
    # Day 1 has no history; after it the league has no home goal yet (Alpha 0-1 Bravo).
    predictions = run_poisson(reversed(season_matches), SETTINGS)

    assert len(predictions) == 10
    assert predictions[0].match.match_date == date(2006, 9, 3)
    assert [p.match for p in predictions] == season_matches[2:]


def test_every_prediction_has_valid_probabilities(season_matches, next_season_matches):
    for prediction in run_poisson([*season_matches, *next_season_matches], SETTINGS):
        probabilities = prediction.distribution.outcome_probabilities()
        assert min(probabilities) >= 0
        assert sum(probabilities) == pytest.approx(1, abs=1e-12)


def test_changing_a_result_never_changes_predictions_on_or_before_its_day(season_matches):
    target = season_matches[6]  # 7 September 2006
    changed = replace(target, home_goals=target.away_goals + 2, result=Outcome.HOME_WIN)

    original = run_poisson(season_matches, SETTINGS)
    after_change = run_poisson([*season_matches[:6], changed, *season_matches[7:]], SETTINGS)

    by_date = {p.match.match_date: numbers(p) for p in original}
    changed_by_date = {p.match.match_date: numbers(p) for p in after_change}
    for day in range(3, 8):
        assert by_date[date(2006, 9, day)] == changed_by_date[date(2006, 9, day)]
    assert any(
        by_date[date(2006, 9, day)] != changed_by_date[date(2006, 9, day)] for day in range(8, 13)
    )


@pytest.mark.parametrize(
    "settings",
    [
        PoissonSettings(team_window=0, prior_matches=1, league_window=380),
        PoissonSettings(team_window=19, prior_matches=0, league_window=380),
        PoissonSettings(team_window=19, prior_matches=1, league_window=0),
        PoissonSettings(team_window=19, prior_matches=1, league_window=380, half_life=0),
        PoissonSettings(team_window=19, prior_matches=1, league_window=380, rho=math.nan),
    ],
)
def test_invalid_settings_are_rejected(season_matches, settings):
    with pytest.raises(ValueError):
        run_poisson(season_matches, settings)
