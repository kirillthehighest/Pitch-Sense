from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from app.algorithms.elo import DEFAULT_INITIAL_RATING
from app.data.models import Outcome
from app.prediction.elo_predictions import run_elo
from app.prediction.outputs import ModelName
from app.prediction.prediction_engine import predict_fixture
from app.services.catalog import DataCatalog
from app.services.evaluation import EvaluationService
from app.services.predictions import PredictionService, summarize
from app.services.teams import GROUP_NAMES, TeamService
from app.statistics.team_statistics import TeamResult

W, D, L = TeamResult.WIN, TeamResult.DRAW, TeamResult.LOSS


@pytest.fixture
def two_seasons(season_matches, next_season_matches):
    return [*season_matches, *next_season_matches]


# --- catalog ---


def test_catalog_lists_seasons_teams_and_matches(database):
    catalog = DataCatalog.load(database)

    assert catalog.seasons() == ["2006-07", "2007-08"]
    assert catalog.teams("2007-08") == ["Alpha", "Bravo", "Charlie", "Delta"]
    matches = catalog.season_matches("2006-07")
    assert len(matches) == 12
    assert [m.match_date for m in matches] == sorted(m.match_date for m in matches)
    summary = catalog.summary()
    assert (summary.competition_name, summary.seasons, summary.matches, summary.teams) == (
        "La Liga",
        2,
        24,
        4,
    )
    assert (summary.first_season, summary.last_season) == ("2006-07", "2007-08")


def test_catalog_explains_a_missing_database(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_database"):
        DataCatalog.load(tmp_path / "missing.db")


def test_catalog_rejects_an_unknown_season(database):
    with pytest.raises(ValueError, match="no matches"):
        DataCatalog.load(database).season_matches("1999-00")


# --- predictions ---


def numbers(fixture):
    return {model: p.probabilities.as_tuple() for model, p in fixture.predictions.items()}


def test_a_played_match_comes_from_the_cache_with_the_same_numbers(two_seasons):
    service = PredictionService(two_seasons, min_training_matches=3)
    match = two_seasons[15]
    direct = predict_fixture(
        two_seasons,
        match.season,
        match.home_team,
        match.away_team,
        match.match_date,
        min_training_matches=3,
    )

    assert not service.is_prepared
    before_preparing = service.predict(
        match.season, match.home_team, match.away_team, match.match_date
    )
    service.prepare()
    from_cache = service.predict(match.season, match.home_team, match.away_team, match.match_date)

    assert service.is_prepared
    assert from_cache.played == match
    assert numbers(from_cache) == numbers(direct) == numbers(before_preparing)


def test_a_hypothetical_fixture_is_predicted_on_request(two_seasons):
    service = PredictionService(two_seasons, min_training_matches=3)
    service.prepare()

    fixture = service.predict("2007-08", "Alpha", "Bravo", date(2007, 9, 5))

    assert fixture.played is None
    assert set(fixture.predictions) == set(ModelName)


def test_summaries_are_ready_to_display(two_seasons):
    service = PredictionService(two_seasons, min_training_matches=3)
    match = two_seasons[15]
    fixture = service.predict(match.season, match.home_team, match.away_team, match.match_date)

    poisson = summarize(fixture.predictions[ModelName.POISSON])
    elo = summarize(fixture.predictions[ModelName.ELO])

    assert poisson.expected_goals is not None
    assert len(poisson.top_scores) == 5
    probabilities = [score[2] for score in poisson.top_scores]
    assert probabilities == sorted(probabilities, reverse=True)
    assert (elo.expected_goals, elo.top_scores) == (None, ())
    distribution = fixture.predictions[ModelName.POISSON].score_distribution
    np.testing.assert_array_equal(poisson.score_probabilities, distribution.probabilities)
    assert elo.score_probabilities is None
    assert elo.home_win + elo.draw + elo.away_win == pytest.approx(1)
    assert isinstance(elo.most_likely, Outcome)


# --- teams ---


def test_end_of_season_table(two_seasons):
    standings = TeamService(two_seasons).standings("2006-07")

    # Alpha 11 points, Bravo 9, Charlie 7, Delta 5 (worked out from the fixture results).
    assert [(row.position, row.team, row.record.points) for row in standings] == [
        (1, "Alpha", 11),
        (2, "Bravo", 9),
        (3, "Charlie", 7),
        (4, "Delta", 5),
    ]


def test_table_as_of_a_date_breaks_ties_by_goal_difference_then_goals(two_seasons):
    standings = TeamService(two_seasons).standings("2006-07", before=date(2006, 9, 4))

    # After 1-3 September: Alpha 6, Bravo 3; Charlie and Delta 0 points and -1 goal difference,
    # but Delta scored once (1-2 at Alpha) and Charlie never.
    assert [row.team for row in standings] == ["Alpha", "Bravo", "Delta", "Charlie"]


def test_overview_of_a_finished_season(two_seasons):
    overview = TeamService(two_seasons).overview("2006-07", "Alpha")

    assert (overview.record.played, overview.record.points, overview.position) == (6, 11, 1)
    assert overview.home.played == overview.away.played == 3
    assert overview.form == (W, W, D, W, D)
    assert overview.season_profile is not None
    assert overview.season_group in GROUP_NAMES.values()
    assert overview.pre_season_group.startswith("Not available")


def test_overview_part_way_through_a_season(two_seasons):
    overview = TeamService(two_seasons).overview("2007-08", "Alpha", before=date(2007, 9, 4))

    assert overview.record.played == 3
    assert overview.season_profile is None
    assert overview.season_group is None
    assert overview.pre_season_group in GROUP_NAMES.values()


def test_overview_rejects_a_team_outside_the_season(two_seasons):
    with pytest.raises(ValueError, match="did not play"):
        TeamService(two_seasons).overview("2007-08", "Zulu")


def test_elo_history_is_the_rating_before_each_match_season_by_season(two_seasons):
    history = TeamService(two_seasons).elo_history("Alpha")

    assert [season.season for season in history] == ["2006-07", "2007-08"]
    assert [len(season.dates) for season in history] == [6, 6]
    assert history[0].ratings[0] == DEFAULT_INITIAL_RATING  # nobody has played yet
    expected = [
        p.home_rating if p.match.home_team == "Alpha" else p.away_rating
        for p in run_elo(two_seasons).predictions
        if "Alpha" in (p.match.home_team, p.match.away_team)
    ]
    assert [rating for season in history for rating in season.ratings] == expected
    dates = [day for season in history for day in season.dates]
    assert dates == sorted(dates)


def test_elo_history_does_not_use_the_result_of_the_match_itself(two_seasons):
    match = next(
        m for m in two_seasons if m.season == "2007-08" and "Alpha" in (m.home_team, m.away_team)
    )
    changed = replace(match, home_goals=9, away_goals=0, result=Outcome.HOME_WIN)
    swapped = [changed if m is match else m for m in two_seasons]

    before = TeamService(two_seasons).elo_history("Alpha")[1]
    after = TeamService(swapped).elo_history("Alpha")[1]

    index = before.dates.index(match.match_date)
    assert after.ratings[: index + 1] == before.ratings[: index + 1]


def test_elo_history_rejects_an_unknown_team(two_seasons):
    with pytest.raises(ValueError, match="no matches"):
        TeamService(two_seasons).elo_history("Zulu")


def test_season_groups_match_the_overview(two_seasons):
    service = TeamService(two_seasons)

    groups = service.season_groups("2006-07")

    assert [point.team for point in groups.teams] == ["Alpha", "Bravo", "Charlie", "Delta"]
    for point in groups.teams:
        overview = service.overview("2006-07", point.team)
        assert GROUP_NAMES[point.group] == overview.season_group
        assert point.goals_scored == overview.record.goals_for_per_match
        assert point.goals_conceded == overview.record.goals_against_per_match
    assert [centre.group for centre in groups.centres] == [0, 1, 2, 3]


def test_season_groups_reject_an_unknown_season(two_seasons):
    with pytest.raises(ValueError, match="no matches"):
        TeamService(two_seasons).season_groups("1999-00")


# --- evaluation ---


def test_evaluation_results_after_building_the_log(database, tmp_path):
    service = EvaluationService(
        tmp_path / "results" / "log.csv",
        database,
        first_evaluation_season="2007-08",
        min_training_matches=3,
    )

    assert not service.has_log
    with pytest.raises(FileNotFoundError, match="backtest"):
        service.results()
    service.build_log()
    results = service.results()

    assert service.has_log
    assert (results.matches, results.first_season, results.last_season) == (
        12,
        "2007-08",
        "2007-08",
    )
    assert len(results.evaluations) == 5
    assert results.differences and len(results.agreements) == 3
    assert [s.label for s in results.by_season] == ["2007-08"]
    assert 0 <= results.all_agree <= 1
    assert service.results() is results  # computed once


def test_a_damaged_log_asks_for_a_new_backtest(tmp_path):
    log = tmp_path / "log.csv"
    log.write_text("not,a,log\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not a prediction log.*Run the backtest again"):
        EvaluationService(log, tmp_path / "pitchsense.db").results()


def test_building_the_log_needs_the_database(tmp_path):
    service = EvaluationService(tmp_path / "log.csv", tmp_path / "missing.db")

    with pytest.raises(FileNotFoundError, match="build_database"):
        service.build_log()
