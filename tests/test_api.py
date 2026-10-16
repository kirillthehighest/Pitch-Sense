"""The local server of the web interface, over the synthetic seasons: every answer is the
services' own, in the shapes the interface reads."""

import os
import threading
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api.__main__ import exit_with_window, option, port_of
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


def test_a_played_matchs_page_has_every_model_the_scores_and_both_teams(client, backend):
    listed = client.get("/api/day/2007-09-03", params={"league": "SP1"}).json()
    forecast = listed["leagues"][0]["forecasts"][0]
    params = {
        "season": forecast["season"],
        "day": forecast["date"],
        "home": forecast["home_team"],
        "away": forecast["away_team"],
    }

    page = client.get("/api/match/SP1", params=params).json()

    assert page["forecast"] == forecast  # the same match as in the day's list
    assert page["status"] == "Final" and page["verdict"].startswith("Rezultat: ")
    assert page["before"] == forecast["date"]
    assert set(page["explanations"]) == {"Elo", "Poisson", "Logistic regression"}
    grid = page["poisson"]["grid"]
    assert len(grid) == 7 and all(len(row) == 7 for row in grid)
    top = page["poisson"]["top_scores"][0]
    assert grid[top["home"]][top["away"]] == pytest.approx(top["probability"])
    assert top["probability"] == max(max(row) for row in grid)
    teams = backend.league("SP1").teams
    before = date.fromisoformat(forecast["date"])
    assert page["home"]["rating"] == teams.rating_before(forecast["home_team"], before)
    assert page["teams"] == len(teams.standings(forecast["season"]))
    assert 1 <= page["away"]["position"] <= page["teams"]
    assert len(page["home"]["form"]) <= 5 and set(page["home"]["form"]) <= {"W", "D", "L"}


def test_any_two_teams_of_a_season_make_a_hypothetical_match(client):
    window = client.get("/api/season/SP1", params={"season": "2006-07"}).json()
    home, away = window["teams"][0], window["teams"][1]
    assert window["first_day"] <= window["suggested_day"] <= window["last_day"]

    params = {"season": "2006-07", "day": window["suggested_day"], "home": home, "away": away}
    page = client.get("/api/match/SP1", params=params).json()

    assert page["forecast"]["hypothetical"] is True
    assert page["status"] == "Meci ipotetic" and page["verdict"] is None
    assert page["forecast"]["predictions"]
    same = client.get("/api/match/SP1", params={**params, "away": home})
    assert same.status_code == 422
    unknown = client.get("/api/match/SP1", params={**params, "home": "Nobody"})
    assert unknown.status_code == 404


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


def test_the_command_line_options():
    assert option(["--port", "8765", "--preferences", "a.json"], "--preferences") == "a.json"
    assert option(["--port", "8765"], "--preferences") is None
    assert port_of([]) == 0 and port_of(["--port", "8765"]) == 8765
    with pytest.raises(SystemExit, match="needs a value"):
        option(["--preferences"], "--preferences")
    with pytest.raises(SystemExit, match="needs a number"):
        port_of(["--port", "eight"])


def test_the_server_ends_when_its_window_closes():
    reading, writing = os.pipe()
    ended = threading.Event()
    with os.fdopen(reading, "rb") as window:
        watcher = exit_with_window(window, end=ended.set)
        assert not ended.wait(0.05)  # the window is still open
        os.close(writing)  # the window's process ended
        watcher.join(timeout=5)
    assert ended.is_set()
