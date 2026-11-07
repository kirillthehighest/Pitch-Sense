"""The server's season at a glance (Phase 25): the models' record and the projected table."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.schemas import likely_score
from app.api.server import create_app
from app.data.models import Outcome
from app.prediction.outputs import ModelName, ModelPrediction, OutcomeProbabilities
from app.prediction.settings import settings_for
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


def test_every_prediction_carries_the_likeliest_score_of_its_own_favourite(api_client):
    found = api_client.get(
        "/api/review/SP1", params={"season": "2007-08", "model": "Poisson"}
    ).json()

    models_seen = set()
    for row in found["rows"]:
        for prediction in row["forecast"]["predictions"]:
            home, away = prediction["likely_score"]
            outcome = "H" if home > away else "A" if home < away else "D"
            assert outcome == prediction["most_likely"]  # never contradicts its own chances
            models_seen.add(prediction["model"])
    assert models_seen == {"Elo", "Poisson", "Logistic regression"}


def test_the_likely_score_is_the_poisson_grids_best_within_the_favourite():
    grid = np.array([[0.10, 0.08, 0.02], [0.20, 0.12, 0.03], [0.15, 0.05, 0.01]])
    draw_pick = ModelPrediction(
        model=ModelName.ELO, probabilities=OutcomeProbabilities(0.3, 0.4, 0.3)
    )
    home_pick = ModelPrediction(
        model=ModelName.ELO, probabilities=OutcomeProbabilities(0.5, 0.3, 0.2)
    )

    assert draw_pick.probabilities.most_likely is Outcome.DRAW
    assert likely_score(draw_pick, grid) == (1, 1)
    assert likely_score(home_pick, grid) == (1, 0)
    assert likely_score(home_pick) is None  # no grid of its own, none given


def test_a_match_page_says_elos_home_advantage(api_client):
    review = api_client.get("/api/review/SP1", params={"season": "2007-08", "model": "Elo"}).json()
    match = review["rows"][0]["forecast"]

    page = api_client.get(
        "/api/match/SP1",
        params={
            "season": match["season"],
            "day": match["date"],
            "home": match["home_team"],
            "away": match["away_team"],
        },
    )

    assert page.status_code == 200
    assert page.json()["elo_home_advantage"] == settings_for("SP1").elo.home_advantage
