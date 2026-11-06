"""The server's season at a glance (Phase 25): the models' record and the projected table."""

import pytest
from fastapi.testclient import TestClient

from app.api.server import create_app
from app.prediction.outputs import ModelName
from app.services.outlook import SIMULATIONS


def test_the_record_sums_each_models_review_of_the_latest_season(api_client, api_backend):
    answer = api_client.get("/api/track-record/SP1")

    assert answer.status_code == 200
    found = answer.json()
    assert found["season"] == "2007-08" and found["in_progress"] is False
    assert [model["model"] for model in found["models"]] == [
        "Logistic regression",
        "Elo",
        "Poisson",
    ]
    for model in found["models"]:
        review = api_backend.league("SP1").predictions.review("2007-08", ModelName(model["model"]))
        assert (model["hits"], model["matches"]) == (review.hits, len(review.matches))
        assert 0 <= model["recent_hits"] <= model["recent_matches"] <= model["matches"]


def test_a_league_without_a_season_in_progress_has_no_projection(api_client):
    answer = api_client.get("/api/projection/SP1")

    assert answer.status_code == 404 and "no season in progress" in answer.json()["detail"]


@pytest.fixture
def live_client(make_backend, database, live_dir):
    backend = make_backend(database, live_dir=live_dir)
    backend.prepare_all(wait=True)
    return TestClient(create_app(backend)), backend


def test_the_projection_plays_every_fixture_of_the_season_in_progress(live_client):
    client, backend = live_client

    found = client.get("/api/projection/SP1").json()

    services = backend.league("SP1")
    assert found["season"] == services.catalog.current_season
    assert found["model"] == "Logistic regression" and found["label"] == "Regresie logistică"
    assert found["fixtures"] + found["unpredicted"] == len(services.predictions.upcoming())
    assert found["simulations"] == SIMULATIONS
    table = {row.team: row for row in services.teams.standings(found["season"])}
    assert {team["team"] for team in found["teams"]} == set(table)
    for team in found["teams"]:
        assert team["points"] == table[team["team"]].record.points
        assert team["expected_points"] >= team["points"]
        assert team["expected_points"] <= team["points"] + 3 * team["remaining"]
        assert sum(team["places"]) == pytest.approx(1.0)
    expected = [team["expected_points"] for team in found["teams"]]
    assert expected == sorted(expected, reverse=True)


def test_the_projection_answers_for_each_model_and_refuses_an_unknown_one(live_client):
    client, _ = live_client

    elo = client.get("/api/projection/SP1", params={"model": "Elo"})
    unknown = client.get("/api/projection/SP1", params={"model": "Oracle"})

    assert elo.status_code == 200 and elo.json()["label"] == "Elo"
    assert unknown.status_code == 404


def test_the_team_page_says_from_which_season_results_are_reported(api_client):
    found = api_client.get("/api/team/SP1", params={"season": "2007-08"}).json()

    assert found["first_evaluated_season"] == "2010-11"
