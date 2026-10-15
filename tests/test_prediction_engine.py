from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.data.models import Fixture, Outcome
from app.prediction.elo_predictions import elo_outcome_predictions, run_elo
from app.prediction.logistic_predictions import run_logistic_regression
from app.prediction.outputs import ModelName
from app.prediction.poisson_predictions import run_poisson
from app.prediction.prediction_engine import (
    predict_fixture,
    predict_history,
    predict_season,
)

ELO, POISSON, LOGISTIC = ModelName.ELO, ModelName.POISSON, ModelName.LOGISTIC_REGRESSION


@pytest.fixture
def two_seasons(season_matches, next_season_matches):
    return [*season_matches, *next_season_matches]


def models_by_day(results, year):
    return {
        r.match.match_date.day: tuple(r.predictions)
        for r in results
        if r.match.match_date.year == year
    }


def test_which_models_predict_which_fixture_days(two_seasons):
    results = predict_history(reversed(two_seasons), min_training_matches=3)

    assert [r.match for r in results] == two_seasons
    first_season = models_by_day(results, 2006)
    # Days 1-2: no league goals at home and away yet. Day 3: Poisson only. Days 4-10: Elo's draw
    # model is fitted on days 1-3, but logistic regression has only 2 training matches (days 2-3).
    assert first_season[1] == first_season[2] == ()
    assert first_season[3] == (POISSON,)
    assert all(first_season[day] == (ELO, POISSON) for day in range(4, 11))
    assert first_season[11] == first_season[12] == (ELO, POISSON, LOGISTIC)
    assert all(r.has_all_models for r in results if r.match.season == "2007-08")


def test_engine_predictions_equal_the_model_runners(two_seasons):
    results = {r.match: r for r in predict_history(two_seasons, min_training_matches=3)}

    for p in elo_outcome_predictions(run_elo(two_seasons), min_matches=3):
        assert results[p.prediction.match].of(ELO).probabilities.as_tuple() == p.probabilities
    for p in run_poisson(two_seasons):
        engine = results[p.match].of(POISSON)
        assert engine.probabilities.as_tuple() == p.distribution.outcome_probabilities()
        assert engine.expected_goals == (
            p.distribution.home_expected_goals,
            p.distribution.away_expected_goals,
        )
    for p in run_logistic_regression(two_seasons, min_training_matches=3):
        assert results[p.match].of(LOGISTIC).probabilities.as_tuple() == p.probabilities


def test_only_poisson_carries_expected_goals_and_a_score_table(two_seasons):
    for result in predict_history(two_seasons, min_training_matches=3):
        for model, prediction in result.predictions.items():
            has_goals = prediction.expected_goals is not None
            has_table = prediction.score_distribution is not None
            assert has_goals == has_table == (model is POISSON)


def test_changing_a_result_never_changes_any_prediction_on_or_before_its_day(two_seasons):
    target = two_seasons[12 + 6]  # 7 September 2007
    changed = replace(target, home_goals=target.away_goals + 2, result=Outcome.HOME_WIN)
    changed_seasons = [*two_seasons[:18], changed, *two_seasons[19:]]

    def numbers(results):
        return {
            r.match.match_date: {
                model: prediction.probabilities.as_tuple()
                for model, prediction in r.predictions.items()
            }
            for r in results
        }

    original = numbers(predict_history(two_seasons, min_training_matches=3))
    after_change = numbers(predict_history(changed_seasons, min_training_matches=3))

    for day, predictions in original.items():
        if day <= date(2007, 9, 7):
            assert after_change[day] == predictions
    assert any(
        original[date(2007, 9, day)] != after_change[date(2007, 9, day)] for day in range(8, 13)
    )


def test_one_competition_at_a_time(two_seasons):
    with pytest.raises(ValueError):
        predict_history([*two_seasons, replace(two_seasons[0], competition="E0")])
    with pytest.raises(ValueError):
        predict_history([])


# --- single fixtures ---


def fixture_numbers(predictions):
    return {
        model: (prediction.probabilities.as_tuple(), prediction.expected_goals)
        for model, prediction in predictions.items()
    }


def test_a_played_fixture_gets_exactly_its_history_prediction(two_seasons):
    history = {r.match: r for r in predict_history(two_seasons, min_training_matches=3)}

    for match in two_seasons[12:]:  # every match of 2007-08
        fixture = predict_fixture(
            two_seasons,
            match.season,
            match.home_team,
            match.away_team,
            match.match_date,
            min_training_matches=3,
        )
        assert fixture.played == match
        assert fixture_numbers(fixture.predictions) == fixture_numbers(history[match].predictions)


def test_a_hypothetical_fixture_gets_what_the_real_match_would_have_got(two_seasons):
    real = two_seasons[12 + 5]  # Bravo v Delta, 6 September 2007
    without_it = [match for match in two_seasons if match is not real]
    history = {r.match: r for r in predict_history(two_seasons, min_training_matches=3)}

    fixture = predict_fixture(
        without_it, "2007-08", "Bravo", "Delta", date(2007, 9, 6), min_training_matches=3
    )

    assert fixture.played is None
    assert fixture_numbers(fixture.predictions) == fixture_numbers(history[real].predictions)


def test_a_hypothetical_fixture_has_every_model_and_valid_probabilities(two_seasons):
    # Alpha hosts Bravo on 1 September 2007, not on the 5th.
    fixture = predict_fixture(
        two_seasons, "2007-08", "Alpha", "Bravo", date(2007, 9, 5), min_training_matches=3
    )

    assert fixture.played is None
    assert tuple(fixture.predictions) == (ELO, POISSON, LOGISTIC)
    for prediction in fixture.predictions.values():
        assert sum(prediction.probabilities.as_tuple()) == pytest.approx(1)


def test_later_seasons_never_change_a_fixture_prediction(two_seasons, season_matches):
    later = [
        replace(m, season="2008-09", match_date=m.match_date.replace(year=2008))
        for m in season_matches
    ]

    alone = predict_fixture(
        two_seasons, "2007-08", "Alpha", "Bravo", date(2007, 9, 5), min_training_matches=3
    )
    with_later = predict_fixture(
        [*two_seasons, *later],
        "2007-08",
        "Alpha",
        "Bravo",
        date(2007, 9, 5),
        min_training_matches=3,
    )

    assert fixture_numbers(alone.predictions) == fixture_numbers(with_later.predictions)


@pytest.mark.parametrize(
    ("season", "home_team", "away_team", "match_date", "message"),
    [
        ("1999-00", "Alpha", "Bravo", date(1999, 9, 1), "no matches"),
        ("2007-08", "Alpha", "Echo", date(2007, 9, 5), "did not play"),
        ("2007-08", "Alpha", "Alpha", date(2007, 9, 5), "itself"),
        ("2007-08", "Alpha", "Bravo", date(2009, 1, 1), "outside season"),
    ],
)
def test_invalid_fixtures_are_rejected(
    two_seasons, season, home_team, away_team, match_date, message
):
    with pytest.raises(ValueError, match=message):
        predict_fixture(two_seasons, season, home_team, away_team, match_date)


# --- the season in progress (Phase 18) ---


@pytest.fixture
def season_in_progress(two_seasons, season_matches):
    """2008-09 after 7 of its 12 matches, and its other 5 matches as fixtures."""
    third = [
        replace(m, season="2008-09", match_date=m.match_date.replace(year=2008))
        for m in season_matches
    ]
    fixtures = [
        Fixture("SP1", "2008-09", m.match_date, m.home_team, m.away_team) for m in third[7:]
    ]
    return [*two_seasons, *third[:7]], fixtures


def test_the_played_matches_keep_their_history_predictions(season_in_progress):
    matches, fixtures = season_in_progress

    history, _ = predict_season(matches, fixtures, min_training_matches=3)

    expected = predict_history(matches, min_training_matches=3)
    assert [r.match for r in history] == [r.match for r in expected]
    for got, want in zip(history, expected, strict=True):
        assert fixture_numbers(got.predictions) == fixture_numbers(want.predictions)


def test_fixtures_are_predicted_from_every_match_played_so_far(season_in_progress):
    matches, fixtures = season_in_progress

    _, upcoming = predict_season(matches, fixtures, min_training_matches=3)

    assert [u.fixture for u in upcoming] == fixtures
    assert {u.as_of for u in upcoming} == {matches[-1].match_date + timedelta(days=1)}
    for prediction in upcoming:
        assert tuple(prediction.predictions) == (ELO, POISSON, LOGISTIC)
        for model in prediction.predictions.values():
            assert sum(model.probabilities.as_tuple()) == pytest.approx(1, abs=1e-9)
            assert min(model.probabilities.as_tuple()) >= 0


def test_fixtures_never_influence_one_another(season_in_progress):
    matches, fixtures = season_in_progress

    _, together = predict_season(matches, fixtures, min_training_matches=3)

    for fixture, prediction in zip(fixtures, together, strict=True):
        _, alone = predict_season(matches, [fixture], min_training_matches=3)
        assert fixture_numbers(alone[0].predictions) == fixture_numbers(prediction.predictions)
    _, reversed_order = predict_season(matches, fixtures[::-1], min_training_matches=3)
    assert [fixture_numbers(u.predictions) for u in reversed_order[::-1]] == [
        fixture_numbers(u.predictions) for u in together
    ]


def test_a_fixture_gets_what_predict_fixture_gives_on_the_day_after_the_last_match(
    season_in_progress,
):
    matches, fixtures = season_in_progress
    fixture = fixtures[0]

    _, upcoming = predict_season(matches, [fixture], min_training_matches=3)
    single = predict_fixture(
        matches,
        "2008-09",
        fixture.home_team,
        fixture.away_team,
        upcoming[0].as_of,
        min_training_matches=3,
    )

    assert fixture_numbers(single.predictions) == fixture_numbers(upcoming[0].predictions)
    assert single.as_of == upcoming[0].as_of


def test_a_played_result_changes_the_fixtures_after_it(season_in_progress):
    matches, fixtures = season_in_progress
    last = matches[-1]
    changed = replace(
        last,
        home_goals=last.away_goals + 3,
        result=Outcome.HOME_WIN,
        statistics=None,
    )

    _, before = predict_season(matches, fixtures, min_training_matches=3)
    _, after = predict_season([*matches[:-1], changed], fixtures, min_training_matches=3)

    assert fixture_numbers(before[0].predictions) != fixture_numbers(after[0].predictions)


@pytest.mark.parametrize(
    ("fixture", "message"),
    [
        (Fixture("SP1", "2007-08", date(2008, 9, 9), "Alpha", "Bravo"), "season 2008-09"),
        (Fixture("E0", "2008-09", date(2008, 9, 9), "Alpha", "Bravo"), "not a SP1 match"),
        (Fixture("SP1", "2008-09", date(2008, 9, 9), "Alpha", "Echo"), "has not played"),
        (Fixture("SP1", "2008-09", date(2008, 9, 9), "Alpha", "Bravo"), "already played"),
    ],
)
def test_invalid_fixtures_of_the_season_in_progress_are_rejected(
    season_in_progress, fixture, message
):
    matches, _ = season_in_progress

    with pytest.raises(ValueError, match=message):
        predict_season(matches, [fixture], min_training_matches=3)


def test_a_fixture_cannot_be_listed_twice(season_in_progress):
    matches, fixtures = season_in_progress

    with pytest.raises(ValueError, match="listed twice"):
        predict_season(matches, [fixtures[0], fixtures[0]], min_training_matches=3)


def test_the_season_in_progress_needs_played_matches():
    with pytest.raises(ValueError, match="at least one played match"):
        predict_season([], [])
