import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from app.algorithms.elo import DEFAULT_INITIAL_RATING
from app.data.live import MANIFEST, LiveLeague, UpdateSummary
from app.data.models import Fixture, Outcome
from app.evaluation.backtesting import log_path, read_log
from app.prediction.elo_predictions import run_elo
from app.prediction.outputs import ModelName
from app.prediction.prediction_engine import predict_fixture, predict_season
from app.services.catalog import DataCatalog, available_competitions
from app.services.evaluation import EvaluationService
from app.services.leagues import LeagueComparisonService
from app.services.predictions import PredictionService, summarize
from app.services.preferences import FavouriteTeam, Preferences
from app.services.teams import FIRST_SEASON_NAME, GROUP_NAMES, NO_STATISTICS_NAME, TeamService
from app.services.updates import summary_text, unmatched_text, updated_text
from app.statistics.team_statistics import TeamResult
from tests.conftest import LIVE_PLAYED, LIVE_SEASON

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
    assert overview.pre_season_group == FIRST_SEASON_NAME


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


def test_a_season_without_shot_statistics_has_no_groups(season_matches, next_season_matches):
    no_statistics = [replace(m, statistics=None) for m in season_matches]
    service = TeamService([*no_statistics, *next_season_matches])

    assert service.overview("2006-07", "Alpha").season_group == NO_STATISTICS_NAME
    assert service.overview("2007-08", "Alpha").pre_season_group == NO_STATISTICS_NAME
    assert service.overview("2007-08", "Alpha").season_group in GROUP_NAMES.values()
    with pytest.raises(ValueError, match="no shot statistics"):
        service.season_groups("2006-07")


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


def test_the_log_of_a_league_is_built_from_that_league(two_league_database, tmp_path):
    service = EvaluationService(
        tmp_path / "backtest_E0.csv",
        two_league_database,
        competition="E0",
        first_evaluation_season="2007-08",
        min_training_matches=3,
    )

    service.build_log()

    teams = {row.home_team for row in read_log(service.log)}
    assert teams == {"Echo", "Foxtrot", "Golf", "Hotel"}
    assert EvaluationService(competition="I1").log == log_path("I1")


# --- leagues ---


def test_available_competitions_are_the_known_leagues_in_registry_order(two_league_database):
    assert available_competitions(two_league_database) == ["E0", "SP1"]


def test_available_competitions_need_the_database(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_database"):
        available_competitions(tmp_path / "missing.db")


@pytest.fixture
def comparison(two_league_database, tmp_path):
    return LeagueComparisonService(
        ("E0", "SP1"),
        tmp_path / "results",
        two_league_database,
        first_evaluation_season="2007-08",
        min_training_matches=3,
    )


def test_the_leagues_are_compared_once_every_log_exists(comparison, tmp_path):
    assert comparison.missing() == ["E0", "SP1"]
    assert comparison.log("SP1") == tmp_path / "results" / "backtest_SP1.csv"
    with pytest.raises(FileNotFoundError, match="E0, SP1"):
        comparison.overview()

    comparison.build_missing_logs()
    overview = comparison.overview()

    assert comparison.missing() == []
    assert [result.competition for result in overview.results] == ["E0", "SP1"]
    assert overview.matches == 24
    assert len(overview.pooled) == 3
    assert comparison.overview() is overview  # computed once


def test_only_the_missing_logs_are_built(comparison):
    comparison.log("SP1").parent.mkdir(parents=True)
    comparison.log("SP1").write_text("kept", encoding="utf-8")

    comparison.build_missing_logs()

    assert comparison.log("SP1").read_text(encoding="utf-8") == "kept"
    assert comparison.log("E0").is_file()


def test_building_the_league_logs_needs_the_database(tmp_path):
    comparison = LeagueComparisonService(("SP1",), tmp_path, tmp_path / "missing.db")

    with pytest.raises(FileNotFoundError, match="build_database"):
        comparison.build_missing_logs()


# --- preferences ---


def test_preferences_start_empty_and_are_remembered(tmp_path):
    path = tmp_path / "PitchSense" / "preferences.json"
    preferences = Preferences(path)
    assert (preferences.competition, preferences.favourite) == (None, None)

    assert preferences.set_competition("E0")
    assert preferences.set_favourite(FavouriteTeam("SP1", "Barcelona"))

    again = Preferences(path)
    assert again.competition == "E0"
    assert again.favourite == FavouriteTeam("SP1", "Barcelona")
    again.set_favourite(None)
    assert Preferences(path).favourite is None
    assert Preferences(path).competition == "E0"


@pytest.mark.parametrize(
    "content",
    ["{not json", "[1, 2]", '{"competition": 3, "favourite": {"team": "Barcelona"}}'],
)
def test_a_damaged_preferences_file_is_ignored(tmp_path, content):
    path = tmp_path / "preferences.json"
    path.write_text(content, encoding="utf-8")

    preferences = Preferences(path)

    assert (preferences.competition, preferences.favourite) == (None, None)
    preferences.set_competition("SP1")
    assert Preferences(path).competition == "SP1"


def test_a_choice_that_cannot_be_saved_lasts_until_the_application_closes(tmp_path):
    blocked = tmp_path / "file"
    blocked.write_text("", encoding="utf-8")  # a file where the folder should be
    preferences = Preferences(blocked / "preferences.json")

    assert not preferences.set_favourite(FavouriteTeam("E0", "Arsenal"))
    assert preferences.favourite == FavouriteTeam("E0", "Arsenal")


# --- the season in progress (Phase 18) ---


def test_the_catalog_adds_the_season_in_progress(database, live_dir):
    catalog = DataCatalog.load(database, competition="SP1", live_dir=live_dir)

    assert catalog.seasons() == ["2006-07", "2007-08", LIVE_SEASON]
    assert catalog.current_season == LIVE_SEASON
    assert len(catalog.season_matches(LIVE_SEASON)) == LIVE_PLAYED
    assert len(catalog.fixtures) == 12 - LIVE_PLAYED
    assert catalog.teams(LIVE_SEASON) == ["Alpha", "Bravo", "Charlie", "Delta"]
    assert catalog.updated_at.tzinfo is not None
    assert catalog.live_problem is None


def test_without_a_download_the_catalog_has_the_completed_seasons(database, tmp_path):
    for live_dir in (None, tmp_path / "never"):
        catalog = DataCatalog.load(database, competition="SP1", live_dir=live_dir)

        assert catalog.seasons() == ["2006-07", "2007-08"]
        assert (catalog.current_season, catalog.fixtures, catalog.live_problem) == (None, (), None)


def test_a_damaged_download_leaves_the_completed_seasons(database, live_dir):
    (live_dir / "SP1.json").write_text("<html>", encoding="utf-8")

    catalog = DataCatalog.load(database, competition="SP1", live_dir=live_dir)

    assert catalog.seasons() == ["2006-07", "2007-08"]
    assert catalog.fixtures == ()
    assert "not a calendar" in catalog.live_problem


def test_a_downloaded_season_already_in_the_database_is_ignored(database, live_dir):
    manifest = json.loads((live_dir / MANIFEST).read_text(encoding="utf-8"))
    manifest["season"] = "2007-08"
    (live_dir / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    for name in ("SP1.csv", "SP1.json"):  # the same rows, one year earlier
        path = live_dir / name
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("/08,", "/07,").replace("2008-09-", "2007-09-"), "utf-8")

    catalog = DataCatalog.load(database, competition="SP1", live_dir=live_dir)

    assert catalog.seasons() == ["2006-07", "2007-08"]
    assert len(catalog.matches) == 24


def test_fixtures_need_their_season(two_seasons):
    fixture = Fixture("SP1", "2008-09", date(2008, 9, 1), "Alpha", "Bravo")

    with pytest.raises(ValueError, match="season in progress"):
        DataCatalog("SP1", two_seasons, (fixture,))
    with pytest.raises(ValueError, match="2007-08"):
        DataCatalog("SP1", two_seasons, (fixture,), current_season="2007-08")


@pytest.fixture
def catalog_in_progress(database, live_dir):
    return DataCatalog.load(database, competition="SP1", live_dir=live_dir)


def test_scheduled_matches_are_predicted_once_from_every_match_played(catalog_in_progress):
    catalog = catalog_in_progress
    service = PredictionService(catalog.matches, catalog.fixtures, min_training_matches=3)

    upcoming = service.upcoming()

    assert service.is_prepared
    _, expected = predict_season(catalog.matches, catalog.fixtures, min_training_matches=3)
    assert [u.fixture for u in upcoming] == list(catalog.fixtures)
    assert [numbers(u) for u in upcoming] == [numbers(u) for u in expected]


def test_a_scheduled_match_gives_the_same_numbers_before_and_after_preparing(
    catalog_in_progress,
):
    catalog = catalog_in_progress
    fixture = catalog.fixtures[2]
    service = PredictionService(catalog.matches, catalog.fixtures, min_training_matches=3)
    ask = (LIVE_SEASON, fixture.home_team, fixture.away_team, fixture.match_date)

    before_preparing = service.predict(*ask)
    service.prepare()
    from_cache = service.predict(*ask)

    as_of = catalog.matches[-1].match_date + timedelta(days=1)
    assert from_cache.played is None
    assert from_cache.as_of == before_preparing.as_of == as_of
    assert numbers(from_cache) == numbers(before_preparing)
    assert numbers(from_cache) == numbers(service.upcoming()[2])


def test_any_later_date_of_the_season_uses_every_match_played(catalog_in_progress):
    catalog = catalog_in_progress
    service = PredictionService(catalog.matches, catalog.fixtures, min_training_matches=3)
    fixture = catalog.fixtures[0]
    service.prepare()

    later = service.predict(LIVE_SEASON, fixture.home_team, fixture.away_team, date(2009, 3, 1))
    played_pair = service.predict(LIVE_SEASON, "Alpha", "Bravo", date(2009, 3, 1))

    assert later.match_date == date(2009, 3, 1)
    assert numbers(later) == numbers(service.upcoming()[0])
    assert played_pair.as_of == later.as_of
    assert set(played_pair.predictions) == set(ModelName)


def test_the_season_in_progress_is_never_grouped(catalog_in_progress, two_seasons):
    catalog = catalog_in_progress
    teams = TeamService(catalog.matches, in_progress=LIVE_SEASON)

    overview = teams.overview(LIVE_SEASON, "Alpha")

    assert overview.in_progress
    assert overview.record.played == 5  # A-B, A-C, A-D, B-A and C-A, the first 7 matches
    assert (overview.season_profile, overview.season_group) == (None, None)
    assert overview.pre_season_group in GROUP_NAMES.values()
    with pytest.raises(ValueError, match="in progress"):
        teams.season_groups(LIVE_SEASON)
    completed = TeamService(two_seasons).season_groups("2007-08")
    assert teams.season_groups("2007-08") == completed  # the partial season changes nothing


def test_only_the_latest_season_can_be_in_progress(two_seasons):
    with pytest.raises(ValueError, match="must be the latest"):
        TeamService(two_seasons, in_progress="2006-07")


def test_an_update_is_described_in_romanian():
    league = LiveLeague(
        "SP1", "2026-27", (), tuple(range(302)), ("Real Charlie",), datetime(2026, 10, 15)
    )
    other = LiveLeague("E0", "2026-27", (), tuple(range(320)), (), datetime(2026, 10, 15))
    summary = UpdateSummary("2026-27", datetime(2026, 10, 15, tzinfo=UTC), (league, other))

    assert summary_text(summary) == (
        "Sezonul 2026/27: 0 meciuri jucate și 622 de meciuri programate în 2 ligi. Echipe din "
        "calendar care nu au putut fi recunoscute, cu meciurile lor lăsate deoparte: La Liga "
        "(Real Charlie)."
    )
    assert unmatched_text(("A", "B")).endswith("potrivite cu siguranță: A, B.")


def test_the_time_of_an_update_is_shown_in_the_local_time_zone():
    moment = datetime(2026, 10, 15, 13, 5, tzinfo=UTC)
    local = moment.astimezone()

    assert updated_text(moment) == f"{local:%d.%m.%Y}, {local:%H:%M}"
