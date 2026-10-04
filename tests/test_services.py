from datetime import date

import pytest

from app.data.models import Outcome
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


def test_building_the_log_needs_the_database(tmp_path):
    service = EvaluationService(tmp_path / "log.csv", tmp_path / "missing.db")

    with pytest.raises(FileNotFoundError, match="build_database"):
        service.build_log()
