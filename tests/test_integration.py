"""End-to-end tests: raw season files -> database -> backtest log -> evaluation -> the answers of
the local server the web interface shows.

Each test runs the whole chain on the small synthetic seasons of conftest.py and checks that the
layers agree with each other, or that a broken input is answered with its reason instead of
stopping the server. (Until Phase 22 the chain ended in the PySide6 window.)
"""

import pytest
from fastapi.testclient import TestClient

from app.api.server import create_app
from app.evaluation.backtesting import read_log
from app.evaluation.evaluator import evaluate
from app.prediction.prediction_engine import predict_season
from app.services.catalog import DataCatalog

MODELS = ("Elo", "Poisson", "Logistic regression")


@pytest.fixture
def backend(make_backend, database):
    served = make_backend(database)
    served.prepare_all(wait=True)
    return served


@pytest.fixture
def client(backend):
    return TestClient(create_app(backend))


@pytest.fixture
def client_with_log(client):
    assert client.post("/api/evaluation/SP1/backtest").status_code == 200
    return client


def test_every_played_match_shows_the_forecasts_of_the_backtest_log(client_with_log, backend):
    log = read_log(backend.league("SP1").evaluation.log)
    logged = {(row.match_date, row.home_team, row.away_team, row.model): row for row in log}
    played = backend.league("SP1").catalog.season_matches("2007-08")

    for match in played:
        day = client_with_log.get(f"/api/day/{match.match_date}", params={"league": "SP1"}).json()
        (forecast,) = day["leagues"][0]["forecasts"]  # one match a day
        rows = {
            model: logged[(match.match_date, match.home_team, match.away_team, model)]
            for model in MODELS
        }
        shown = {prediction["model"]: prediction for prediction in forecast["predictions"]}
        assert set(shown) == set(MODELS)
        for model, row in rows.items():
            assert (shown[model]["home"], shown[model]["draw"], shown[model]["away"]) == (
                row.p_home,
                row.p_draw,
                row.p_away,
            )
            assert shown[model]["hit"] == (row.predicted == row.actual)

        page = client_with_log.get(
            "/api/match/SP1",
            params={
                "season": match.season,
                "day": match.match_date.isoformat(),
                "home": match.home_team,
                "away": match.away_team,
            },
        ).json()
        poisson = rows["Poisson"]
        assert page["poisson"]["expected_goals"] == [
            poisson.expected_home_goals,
            poisson.expected_away_goals,
        ]
        assert (page["forecast"]["home_goals"], page["forecast"]["away_goals"]) == (
            match.home_goals,
            match.away_goals,
        )
        assert page["status"] == "Final"
    assert len(played) == 12


def test_the_screens_show_the_evaluation_of_the_log(client_with_log, backend):
    evaluations = evaluate(read_log(backend.league("SP1").evaluation.log))

    shown = client_with_log.get("/api/evaluation/SP1").json()["models"]

    assert [
        (m["model"], m["accuracy"], m["brier"], m["log_loss"], m["calibration_error"])
        for m in shown
    ] == [
        (
            e.model,
            e.accuracy.value,
            e.brier.value if e.brier else None,
            e.log_loss.value if e.log_loss else None,
            e.calibration_error,
        )
        for e in evaluations
    ]


@pytest.mark.parametrize("season", ["2006-07", "2007-08"])
def test_the_league_table_matches_the_raw_files(client, raw_season_rows, next_season_rows, season):
    raw_rows = raw_season_rows if season == "2006-07" else next_season_rows
    records = {}
    for row in raw_rows:
        home_goals, away_goals = int(row["FTHG"]), int(row["FTAG"])
        for team, scored, conceded in (
            (row["HomeTeam"], home_goals, away_goals),
            (row["AwayTeam"], away_goals, home_goals),
        ):
            played, wins, draws, losses, goals_for, goals_against = records.get(team, [0] * 6)
            records[team] = [
                played + 1,
                wins + (scored > conceded),
                draws + (scored == conceded),
                losses + (scored < conceded),
                goals_for + scored,
                goals_against + conceded,
            ]
    expected = sorted(
        records.items(),
        key=lambda item: (
            -(3 * item[1][1] + item[1][2]),
            -(item[1][4] - item[1][5]),
            -item[1][4],
            item[0],
        ),
    )

    table = client.get("/api/standings/SP1", params={"season": season}).json()

    keys = ("played", "wins", "draws", "losses", "goals_for", "goals_against")
    assert [
        (
            row["position"],
            row["team"],
            *(row["record"][key] for key in keys),
            row["record"]["goal_difference"],
            row["record"]["points"],
        )
        for row in table["rows"]
    ] == [
        (position, team, *record, record[4] - record[5], 3 * record[1] + record[2])
        for position, (team, record) in enumerate(expected, start=1)
    ]


def test_a_damaged_log_is_explained_in_place_and_can_be_rebuilt(client, backend):
    log = backend.league("SP1").evaluation.log
    log.parent.mkdir(parents=True)
    log.write_text("not,a,prediction,log\n1,2,3,4\n", encoding="utf-8")

    for answer in (
        client.get("/api/evaluation/SP1").json(),
        client.get("/api/leagues-comparison").json(),
    ):
        assert "is not a prediction log" in answer["problem"]  # the details, in place

    rebuilt = client.post("/api/evaluation/SP1/backtest").json()

    assert rebuilt["problem"] is None and len(rebuilt["models"]) == 5
    assert len(client.get("/api/leagues-comparison").json()["results"]) == 1


def test_a_backtest_that_fails_is_reported_and_the_server_keeps_working(client, database):
    database.unlink()  # the data is already loaded; the backtest reads the database again

    answer = client.post("/api/evaluation/SP1/backtest")

    assert answer.status_code == 500 and "Database not found" in answer.json()["detail"]
    table = client.get("/api/standings/SP1", params={"season": "2006-07"}).json()
    assert len(table["rows"]) == 4  # the loaded data still works


def test_every_scheduled_match_shows_the_engines_forecast_from_the_downloads(
    make_backend, database, live_dir
):
    # raw files -> database, downloads -> season in progress -> engine and server agree
    catalog = DataCatalog.load(database, competition="SP1", live_dir=live_dir)
    _, upcoming = predict_season(catalog.matches, catalog.fixtures, min_training_matches=3)
    backend = make_backend(database, live_dir=live_dir)
    backend.prepare_all(wait=True)
    client = TestClient(create_app(backend))

    for expected in upcoming:
        fixture = expected.fixture
        day = client.get(f"/api/day/{fixture.match_date}", params={"league": "SP1"}).json()
        (forecast,) = day["leagues"][0]["forecasts"]
        assert (forecast["home_team"], forecast["away_team"]) == (
            fixture.home_team,
            fixture.away_team,
        )
        assert [(p["model"], p["home"], p["draw"], p["away"]) for p in forecast["predictions"]] == [
            (
                str(model),
                prediction.probabilities.home_win,
                prediction.probabilities.draw,
                prediction.probabilities.away_win,
            )
            for model, prediction in expected.predictions.items()
        ]
        page = client.get(
            "/api/match/SP1",
            params={
                "season": fixture.season,
                "day": fixture.match_date.isoformat(),
                "home": fixture.home_team,
                "away": fixture.away_team,
            },
        ).json()
        assert page["status"] == "Programat" and page["forecast"]["result"] is None
