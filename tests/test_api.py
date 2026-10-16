"""The local server of the web interface, over the synthetic seasons: every answer is the
services' own, in the shapes the interface reads."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api.backend import Backend
from app.api.server import create_app
from app.services.preferences import Preferences
from app.services.processes import compute_here


@pytest.fixture
def backend(make_app_context, two_league_database, tmp_path):
    context = make_app_context(two_league_database, ("E0", "SP1"))
    served = Backend(
        context.competitions,
        open_league=context.open_league,
        comparison=context.comparison,
        preferences=Preferences(tmp_path / "web-preferences.json"),
        compute=compute_here,
        today=lambda: date(2007, 9, 4),
    )
    served.prepare_all(wait=True)
    return served


@pytest.fixture
def client(backend):
    return TestClient(create_app(backend))


def test_the_leagues_come_with_their_seasons_and_state(client):
    leagues = client.get("/api/leagues").json()

    assert [league["code"] for league in leagues] == ["E0", "SP1"]
    assert leagues[1]["name"] == "La Liga" and leagues[1]["country"] == "Spania"
    assert leagues[1]["seasons"] == ["2006-07", "2007-08"]
    assert all(league["prepared"] for league in leagues)
    status = client.get("/api/status").json()
    assert status == {"prepared": {"E0": True, "SP1": True}, "preparing": None, "failures": {}}


def test_the_days_and_the_next_day_with_matches(client):
    days = client.get("/api/days").json()

    assert days["today"] == "2007-09-04"
    assert days["next_day"] >= "2007-09-04"
    assert days["days"] == sorted(days["days"])


def test_a_day_lists_every_league_the_chosen_first_with_predictions(client, backend):
    day = client.get("/api/days").json()["next_day"]
    answer = client.get(f"/api/day/{day}", params={"league": "SP1"}).json()

    assert [group["code"] for group in answer["leagues"]][0] == "SP1"
    forecast = answer["leagues"][0]["forecasts"][0]
    services = backend.league("SP1").predictions.on_day(date.fromisoformat(day))[0]
    assert (forecast["home_team"], forecast["away_team"]) == (
        services.home_team,
        services.away_team,
    )
    for prediction in forecast["predictions"]:
        assert prediction["home"] + prediction["draw"] + prediction["away"] == pytest.approx(1)
        assert prediction["most_likely"] in ("H", "D", "A")
    assert {p["label"] for p in forecast["predictions"]} <= {"Elo", "Poisson", "Regresie logistică"}
    assert answer["featured"] is not None


def test_a_played_match_says_whether_each_model_was_right(client):
    answer = client.get("/api/day/2007-09-03", params={"league": "SP1"}).json()
    forecast = answer["leagues"][0]["forecasts"][0]

    assert forecast["result"] in ("H", "D", "A")
    for prediction in forecast["predictions"]:
        assert prediction["hit"] == (prediction["most_likely"] == forecast["result"])


def test_the_match_of_the_day_is_your_teams(client):
    day = client.get("/api/days").json()["next_day"]
    first = client.get(f"/api/day/{day}", params={"league": "SP1"}).json()["leagues"][0]
    team = first["forecasts"][-1]["away_team"]
    client.put(
        "/api/preferences",
        json={"competition": "SP1", "favourite": {"competition": "SP1", "team": team}},
    )

    featured = client.get(f"/api/day/{day}", params={"league": "SP1"}).json()["featured"]

    assert team in (featured["home_team"], featured["away_team"])


def test_preferences_are_kept(client):
    assert client.get("/api/preferences").json() == {"competition": None, "favourite": None}
    answer = client.put(
        "/api/preferences",
        json={"competition": "E0", "favourite": {"competition": "E0", "team": "Echo"}},
    ).json()
    assert answer == {"competition": "E0", "favourite": {"competition": "E0", "team": "Echo"}}
    assert client.get("/api/preferences").json() == answer
    assert (
        client.put("/api/preferences", json={"competition": "XX", "favourite": None}).status_code
        == 404
    )


def test_images_are_served_and_a_missing_one_is_404(client):
    assert client.get("/api/images/league/SP1").headers["content-type"] == "image/jpeg"
    assert client.get("/api/images/crest/Barcelona").headers["content-type"] == "image/png"
    assert client.get("/api/images/crest/Alpha").status_code == 404
    assert client.get("/api/day/2007-09-03", params={"league": "XX"}).status_code == 404
