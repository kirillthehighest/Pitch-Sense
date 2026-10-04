from dataclasses import replace
from datetime import date

import pytest

from app.data.models import Outcome
from app.prediction.elo_predictions import elo_outcome_predictions, run_elo
from app.prediction.logistic_predictions import run_logistic_regression
from app.prediction.outputs import ModelName
from app.prediction.poisson_predictions import run_poisson
from app.prediction.prediction_engine import predict_fixture, predict_history

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
