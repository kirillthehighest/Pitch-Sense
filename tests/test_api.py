"""The local server of the web interface, over the synthetic seasons: every answer is the
services' own, in the shapes the interface reads."""

import io
import json
import os
import socket
import threading
import time
from datetime import UTC, date, datetime, timedelta

import pytest

from app.api import __main__ as server_main
from app.api.__main__ import HOST, exit_with_window, open_listener, option, port_of, write_utf8
from app.api.self_test import run_self_test
from app.data.live import UpdateSummary
from app.prediction.outputs import ModelName
from app.services.images import STADIUMS_DIR, stadium_name, stadium_path, stadium_teams
from app.services.processes import compute_here


def test_the_leagues_come_with_their_seasons_and_state(api_client):
    leagues = api_client.get("/api/leagues").json()

    assert [league["code"] for league in leagues] == ["E0", "SP1"]
    assert leagues[1]["name"] == "La Liga" and leagues[1]["country"] == "Spania"
    assert leagues[1]["seasons"] == ["2006-07", "2007-08"]
    assert all(league["prepared"] for league in leagues)
    status = api_client.get("/api/status").json()
    assert status == {
        "prepared": {"E0": True, "SP1": True},
        "preparing": None,
        "failures": {},
        "version": 0,
        "updating": False,
    }


def test_the_days_and_the_next_day_with_matches(api_client):
    days = api_client.get("/api/days").json()

    assert days["today"] == "2007-09-04"
    assert days["next_day"] >= "2007-09-04"
    assert days["days"] == sorted(days["days"])


def test_the_next_day_is_the_chosen_leagues_next_match_day(api_client, api_backend):
    days = api_client.get("/api/days", params={"league": "SP1"}).json()
    own = api_backend.league("SP1").predictions.match_days()
    today = date.fromisoformat(days["today"])

    assert days["next_day"] == next(day for day in own if day >= today).isoformat()
    unknown = api_client.get("/api/days", params={"league": "XX"}).json()
    assert unknown["next_day"] == api_client.get("/api/days").json()["next_day"]  # all leagues


def test_a_day_lists_every_league_the_chosen_first_with_predictions(api_client, api_backend):
    day = api_client.get("/api/days").json()["next_day"]
    answer = api_client.get(f"/api/day/{day}", params={"league": "SP1"}).json()

    assert [group["code"] for group in answer["leagues"]][0] == "SP1"
    forecast = answer["leagues"][0]["forecasts"][0]
    services = api_backend.league("SP1").predictions.on_day(date.fromisoformat(day))[0]
    assert (forecast["home_team"], forecast["away_team"]) == (
        services.home_team,
        services.away_team,
    )
    for prediction in forecast["predictions"]:
        assert prediction["home"] + prediction["draw"] + prediction["away"] == pytest.approx(1)
        assert prediction["most_likely"] in ("H", "D", "A")
    assert {p["label"] for p in forecast["predictions"]} <= {"Elo", "Poisson", "Regresie logistică"}
    assert answer["featured"] is not None


def test_a_played_match_says_whether_each_model_was_right(api_client):
    answer = api_client.get("/api/day/2007-09-03", params={"league": "SP1"}).json()
    forecast = answer["leagues"][0]["forecasts"][0]

    assert forecast["result"] in ("H", "D", "A")
    for prediction in forecast["predictions"]:
        assert prediction["hit"] == (prediction["most_likely"] == forecast["result"])


def test_the_match_of_the_day_is_your_teams(api_client):
    day = api_client.get("/api/days").json()["next_day"]
    first = api_client.get(f"/api/day/{day}", params={"league": "SP1"}).json()["leagues"][0]
    team = first["forecasts"][-1]["away_team"]
    api_client.put(
        "/api/preferences",
        json={"competition": "SP1", "favourite": {"competition": "SP1", "team": team}},
    )

    featured = api_client.get(f"/api/day/{day}", params={"league": "SP1"}).json()["featured"]

    assert team in (featured["home_team"], featured["away_team"])


def test_a_played_matchs_page_has_every_model_the_scores_and_both_teams(api_client, api_backend):
    listed = api_client.get("/api/day/2007-09-03", params={"league": "SP1"}).json()
    forecast = listed["leagues"][0]["forecasts"][0]
    params = {
        "season": forecast["season"],
        "day": forecast["date"],
        "home": forecast["home_team"],
        "away": forecast["away_team"],
    }

    page = api_client.get("/api/match/SP1", params=params).json()

    assert page["forecast"] == forecast  # the same match as in the day's list
    assert page["status"] == "Final" and page["verdict"].startswith("Rezultat: ")
    assert page["before"] == forecast["date"]
    assert set(page["explanations"]) == {"Elo", "Poisson", "Logistic regression"}
    grid = page["poisson"]["grid"]
    assert len(grid) == 7 and all(len(row) == 7 for row in grid)
    top = page["poisson"]["top_scores"][0]
    assert grid[top["home"]][top["away"]] == pytest.approx(top["probability"])
    assert top["probability"] == max(max(row) for row in grid)
    teams = api_backend.league("SP1").teams
    before = date.fromisoformat(forecast["date"])
    assert page["home"]["rating"] == teams.rating_before(forecast["home_team"], before)
    assert page["teams"] == len(teams.standings(forecast["season"]))
    assert 1 <= page["away"]["position"] <= page["teams"]
    assert len(page["home"]["form"]) <= 5 and set(page["home"]["form"]) <= {"W", "D", "L"}


def test_any_two_teams_of_a_season_make_a_hypothetical_match(api_client):
    window = api_client.get("/api/season/SP1", params={"season": "2006-07"}).json()
    home, away = window["teams"][0], window["teams"][1]
    assert window["first_day"] <= window["suggested_day"] <= window["last_day"]

    params = {"season": "2006-07", "day": window["suggested_day"], "home": home, "away": away}
    page = api_client.get("/api/match/SP1", params=params).json()

    assert page["forecast"]["hypothetical"] is True
    assert page["status"] == "Meci ipotetic" and page["verdict"] is None
    assert page["forecast"]["predictions"]
    same = api_client.get("/api/match/SP1", params={**params, "away": home})
    assert same.status_code == 422
    unknown = api_client.get("/api/match/SP1", params={**params, "home": "Nobody"})
    assert unknown.status_code == 404


def test_the_table_of_a_whole_season_and_before_a_day(api_client, api_backend):
    teams = api_backend.league("SP1").teams
    whole = api_client.get("/api/standings/SP1", params={"season": "2006-07"}).json()

    assert whole["whole_season"] is True and whole["in_progress"] is False
    assert whole["before"] == teams.season_end("2006-07").isoformat()
    expected = teams.standings("2006-07")
    assert [row["team"] for row in whole["rows"]] == [row.team for row in expected]
    assert [row["position"] for row in whole["rows"]] == list(range(1, len(expected) + 1))
    for row in whole["rows"]:
        record = row["record"]
        assert record["goal_difference"] == record["goals_for"] - record["goals_against"]
        assert len(row["form"]) == 5

    matches = api_backend.league("SP1").catalog.season_matches("2006-07")
    day = matches[len(matches) // 2].match_date.isoformat()
    earlier = api_client.get(
        "/api/standings/SP1", params={"season": "2006-07", "before": day}
    ).json()
    assert earlier["whole_season"] is False and earlier["before"] == day
    played = {row["team"]: row["record"]["played"] for row in earlier["rows"]}
    assert played == {
        row.team: row.record.played for row in teams.standings("2006-07", date.fromisoformat(day))
    }
    assert api_client.get("/api/standings/SP1", params={"season": "1999-00"}).status_code == 404


def test_a_team_page_has_its_season_its_ratings_and_its_groups(api_client, api_backend):
    teams = api_backend.league("SP1").teams
    leader = teams.standings("2006-07")[0].team

    page = api_client.get("/api/team/SP1", params={"season": "2006-07"}).json()

    assert page["team"] == leader and page["position"] == 1  # no favourite: the leader
    overview = teams.overview("2006-07", leader)
    assert page["record"]["points"] == overview.record.points
    assert page["home"]["played"] + page["away"]["played"] == page["record"]["played"]
    assert page["season_group"] == overview.season_group
    history = teams.elo_history(leader)
    assert [s["season"] for s in page["elo"]] == [s.season for s in history]
    assert [p["rating"] for p in page["elo"][0]["points"]] == list(history[0].ratings)
    groups = teams.season_groups("2006-07")
    assert len(page["groups"]["teams"]) == len(groups.teams)
    assert page["groups"]["names"]["0"] == "Elită"
    assert page["groups_problem"] is None


def test_a_team_page_opens_on_your_team_and_refuses_an_absent_team(api_client, api_backend):
    last = api_backend.league("SP1").teams.standings("2006-07")[-1].team  # not the leader
    api_client.put(
        "/api/preferences",
        json={"competition": "SP1", "favourite": {"competition": "SP1", "team": last}},
    )
    assert api_client.get("/api/team/SP1", params={"season": "2006-07"}).json()["team"] == last
    absent = api_client.get("/api/team/SP1", params={"season": "2006-07", "team": "Nobody"})
    assert absent.status_code == 404


def test_a_review_counts_hits_and_surprises_of_a_model(api_client, api_backend):
    answer = api_client.get(
        "/api/review/SP1", params={"season": "2007-08", "model": "Logistic regression"}
    ).json()

    found = api_backend.league("SP1").predictions.review("2007-08", ModelName.LOGISTIC_REGRESSION)
    assert answer["label"] == "Regresie logistică"
    assert (answer["matches"], answer["hits"], answer["surprises"]) == (
        len(found.matches),
        found.hits,
        found.surprises,
    )
    assert [r["result"] for r in answer["by_result"]] == ["H", "D", "A"]
    assert sum(r["matches"] for r in answer["by_result"]) == answer["matches"]
    for sure in answer["sure"]:
        chosen = [r for r in answer["rows"] if r["confidence"] >= sure["threshold"]]
        assert (sure["hits"], sure["matches"]) == (sum(r["hit"] for r in chosen), len(chosen))
    for row in answer["rows"]:
        prediction = next(
            p for p in row["forecast"]["predictions"] if p["model"] == "Logistic regression"
        )
        assert row["hit"] == prediction["hit"]
        assert row["surprise"] == (row["chance"] < answer["surprise_chance"])
    unknown = api_client.get("/api/review/SP1", params={"season": "2007-08", "model": "Oracle"})
    assert unknown.status_code == 404


def test_the_match_of_the_day_follows_the_chosen_league(api_client, api_backend):
    first_e0 = api_backend.league("E0").predictions.match_days()[0]
    before = (first_e0 - timedelta(days=3)).isoformat()  # no English match that day
    api_client.put(  # your team plays in the other league
        "/api/preferences",
        json={"competition": "E0", "favourite": {"competition": "SP1", "team": "Alpha"}},
    )

    featured = api_client.get(f"/api/day/{before}", params={"league": "E0"}).json()["featured"]

    assert featured["competition"] == "E0"
    assert featured["date"] == first_e0.isoformat()  # the league's next day with matches
    spanish = api_client.get(f"/api/day/{before}", params={"league": "SP1"}).json()["featured"]
    assert spanish["competition"] == "SP1"


def test_preferences_are_kept(api_client):
    assert api_client.get("/api/preferences").json() == {"competition": None, "favourite": None}
    answer = api_client.put(
        "/api/preferences",
        json={"competition": "E0", "favourite": {"competition": "E0", "team": "Echo"}},
    ).json()
    assert answer == {"competition": "E0", "favourite": {"competition": "E0", "team": "Echo"}}
    assert api_client.get("/api/preferences").json() == answer
    assert (
        api_client.put(
            "/api/preferences", json={"competition": "XX", "favourite": None}
        ).status_code
        == 404
    )


def test_images_are_served_and_a_missing_one_is_404(api_client):
    assert api_client.get("/api/images/league/SP1").headers["content-type"] == "image/jpeg"
    assert api_client.get("/api/images/crest/Barcelona").headers["content-type"] == "image/png"
    assert api_client.get("/api/images/crest/Alpha").status_code == 404
    stadium = api_client.get("/api/images/stadium/Barcelona")
    assert (
        stadium.headers["content-type"] == "image/jpeg" and stadium.content[:3] == b"\xff\xd8\xff"
    )
    assert api_client.get("/api/images/stadium/Alpha").status_code == 404
    assert api_client.get("/api/day/2007-09-03", params={"league": "XX"}).status_code == 404


def test_a_failed_update_keeps_the_data(api_client, api_backend):
    opened = api_backend.league("SP1")

    answer = api_client.post("/api/update")

    assert answer.status_code == 502 and "network" in answer.json()["detail"]
    assert api_backend.league("SP1") is opened  # nothing was read again


def test_an_update_reads_every_league_again(api_client, api_backend):
    opened = api_backend.league("SP1")
    api_backend.update_data = lambda: UpdateSummary("2008-09", datetime(2008, 9, 8, tzinfo=UTC), ())

    answer = api_client.post("/api/update").json()

    assert answer["summary"].startswith("Sezonul 2008/09: ")
    api_backend.prepare_all(wait=True)
    assert api_backend.league("SP1") is not opened
    assert api_backend.is_prepared("SP1") and api_backend.is_prepared("E0")


def test_an_update_serves_the_previous_predictions_until_the_new_ones_are_ready(
    api_client, api_backend
):
    opened = api_backend.league("SP1")
    started, release = threading.Event(), threading.Event()

    def slow(job):
        started.set()
        release.wait(10)
        return compute_here(job)

    api_backend.compute = slow
    api_backend.update_data = lambda: UpdateSummary("2008-09", datetime(2008, 9, 8, tzinfo=UTC), ())

    assert api_client.post("/api/update").status_code == 200
    assert started.wait(10)  # the new predictions are being computed...
    status = api_client.get("/api/status").json()
    assert api_backend.league("SP1") is opened  # ...while the previous ones answer
    assert all(status["prepared"].values()) and status["version"] == 0

    release.set()
    api_backend.prepare_all(wait=True)
    assert api_backend.league("SP1") is not opened
    assert api_client.get("/api/status").json()["version"] == 2  # both leagues replaced


def test_the_command_line_options():
    assert option(["--port", "8765", "--preferences", "a.json"], "--preferences") == "a.json"
    assert option(["--port", "8765"], "--preferences") is None
    assert port_of([]) == 0 and port_of(["--port", "8765"]) == 8765
    with pytest.raises(SystemExit, match="needs a value"):
        option(["--preferences"], "--preferences")
    with pytest.raises(SystemExit, match="needs a number"):
        port_of(["--port", "eight"])


@pytest.mark.parametrize(
    "origin", ["tauri://localhost", "http://tauri.localhost", "http://localhost:1420"]
)
def test_the_window_s_origin_may_read_the_answers(api_client, origin):
    # macOS's window, Windows' window and the development server
    answer = api_client.get("/api/status", headers={"Origin": origin})

    assert answer.headers["access-control-allow-origin"] == origin


def test_another_origin_may_not_read_the_answers(api_client):
    answer = api_client.get("/api/status", headers={"Origin": "https://example.com"})

    assert "access-control-allow-origin" not in answer.headers


def test_the_port_takes_connections_as_soon_as_it_is_announced():
    # The window asks at once. A socket only bound does not take the connection: Windows refuses
    # it on the spot (the package's "Failed to fetch"), macOS leaves it unanswered. One listening
    # keeps it until uvicorn takes it.
    bound = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bound.bind((HOST, 0))
    listener = open_listener(0)
    try:
        with pytest.raises(OSError):  # ConnectionRefusedError, or TimeoutError on macOS
            socket.create_connection((HOST, bound.getsockname()[1]), timeout=0.5)
        with socket.create_connection((HOST, listener.getsockname()[1]), timeout=2):
            pass
    finally:
        bound.close()
        listener.close()


def test_the_server_ends_when_its_window_closes():
    reading, writing = os.pipe()
    ended = threading.Event()
    with os.fdopen(reading, "rb") as window:
        watcher = exit_with_window(window, end=ended.set)
        assert not ended.wait(0.05)  # the window is still open
        os.close(writing)  # the window's process ended
        watcher.join(timeout=5)
    assert ended.is_set()


def test_the_self_test_asks_the_server_everything(api_backend):
    for code in api_backend.competitions:
        api_backend.league(code).evaluation.build_log()
    api_backend.comparison.build_missing_logs()
    lines: list[str] = []

    result = run_self_test(api_backend, report=lines.append)

    passed = {
        line.split(":")[0].removeprefix("ok").strip() for line in lines if line.startswith("ok")
    }
    assert {
        "predictions",
        "leagues",
        "day",
        "match",
        "standings",
        "team",
        "predictions review",
        "evaluation",
        "leagues comparison",
        "explanations",
        "league image",
    } <= passed
    # the synthetic clubs have neither crests nor stadium photos
    assert any(line.startswith("FAILED  crest") for line in lines)
    assert result == 1 and lines[-1].endswith("checks failed")


def test_every_stadium_photo_has_its_source_and_is_used():
    sources = json.loads((STADIUMS_DIR / "sources.json").read_text(encoding="utf-8"))
    teams = [source["team"] for source in sources]
    photos = {path.stem for path in STADIUMS_DIR.glob("*.jpg")}

    assert len(teams) == len(set(teams)) and teams == sorted(teams)
    assert {source["image"] for source in sources} == photos
    for source in sources:
        assert source["file"].startswith("https://commons.wikimedia.org/wiki/File:")
        assert stadium_path(source["team"]) == STADIUMS_DIR / f"{source['image']}.jpg"
        assert stadium_name(source["team"]) == source["stadium"].split(" (")[0]
    assert stadium_teams() == teams
    assert stadium_name("Ein Frankfurt") == "Waldstadion"
    assert stadium_path("Alpha") is None and stadium_name("Alpha") is None


def test_waiting_for_the_predictions_waits_for_a_preparation_already_running(
    make_backend, two_league_database
):
    started = threading.Event()

    def slow(job):
        started.set()
        time.sleep(0.2)
        return compute_here(job)

    backend = make_backend(two_league_database, ("E0", "SP1"), compute=slow)
    backend.prepare_all()  # in the background
    assert started.wait(5)

    backend.prepare_all(wait=True)

    assert backend.is_prepared("E0") and backend.is_prepared("SP1")


def test_the_server_writes_utf8_whatever_the_console(monkeypatch):
    console = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr("sys.stdout", console)

    write_utf8()
    print("Sezonul 2026/27: 78 de meciuri jucate și programate", file=console, flush=True)

    written = console.buffer.getvalue().decode("utf-8")
    assert written.rstrip().endswith("și programate")  # \r\n on Windows


def test_a_missing_database_is_explained_at_start_up(monkeypatch, capsys):
    calls = []

    def missing(preferences=None):
        calls.append("load")
        raise FileNotFoundError("Database not found: data/pitchsense.db")

    monkeypatch.setattr(server_main, "copy_bundled", lambda: calls.append("copy"))
    monkeypatch.setattr(server_main.Backend, "from_database", missing)

    assert server_main.main([]) == 1
    assert calls == ["copy", "load"]  # the shipped results reach the user's folder first
    error = capsys.readouterr().err
    assert error.startswith("Baza de date nu a fost găsită.")
    assert "python -m app.data.build_database" in error


def test_a_failed_copy_is_reported_and_start_up_goes_on(monkeypatch, capsys):
    def read_only():
        raise PermissionError("read-only folder")

    monkeypatch.setattr(server_main, "copy_bundled_results", read_only)
    monkeypatch.setattr(server_main, "copy_bundled_live", lambda: None)
    monkeypatch.setattr(
        server_main,
        "update_season",
        lambda: UpdateSummary("2026-27", datetime(2026, 10, 16, tzinfo=UTC), ()),
    )

    assert server_main.main(["--update"]) == 0
    written = capsys.readouterr()
    assert written.err == "Jurnalele predicțiilor nu au putut fi copiate: read-only folder\n"
    assert written.out.startswith("Sezonul 2026/27: ")
