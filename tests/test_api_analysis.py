"""The routes of Analiză over the synthetic seasons: the explanations and sources, the models on
the season in progress, a league's backtest and the comparison of the leagues, each the
services' own numbers."""

import pytest

from app.evaluation.comparison import COMPARED_MODELS, REFERENCE_MODEL
from app.services.explanations import EXPLANATIONS, GROUPS_EXPLANATION, SOURCES


def test_the_explanations_and_the_sources(api_client):
    about = api_client.get("/api/about").json()

    assert [e["title"] for e in about["explanations"]] == [title for title, _ in EXPLANATIONS]
    assert about["groups"] == GROUPS_EXPLANATION
    assert [s["title"] for s in about["sources"]] == [title for title, _ in SOURCES]
    assert about["crests"] > 0 and about["stadiums"] > 0 and about["images_note"]


def test_without_a_downloaded_season_the_check_says_so(api_client):
    check = api_client.get("/api/season-check/SP1").json()

    assert check["state"] == "missing" and check["season"] is None and check["models"] == []


def test_a_league_without_a_log_offers_its_backtest(api_client):
    before = api_client.get("/api/evaluation/SP1").json()
    assert (before["has_log"], before["models"], before["problem"]) == (False, [], None)

    built = api_client.post("/api/evaluation/SP1/backtest").json()

    assert built["has_log"] is True and built["problem"] is None
    assert built["compared"] == [*COMPARED_MODELS, REFERENCE_MODEL]
    assert built["first_season"] == built["last_season"] == "2007-08"
    models = {m["model"]: m for m in built["models"]}
    assert set(COMPARED_MODELS) <= set(models)
    for model in COMPARED_MODELS:
        evaluation = models[model]
        assert evaluation["matches"] == built["matches"]
        assert 0 <= evaluation["accuracy"] <= 1 and evaluation["brier"] is not None
        confusion = evaluation["confusion"]
        assert sum(map(sum, confusion)) == built["matches"]
        assert sum(b["count"] for b in evaluation["calibration"]) == 3 * built["matches"]
    assert models["Poisson"]["goals_error"] is not None
    assert models["Elo"]["goals_error"] is None
    for difference in built["differences"]:
        assert difference["lower"] <= difference["mean"] <= difference["upper"]
        real = difference["lower"] > 0 or difference["upper"] < 0
        assert (difference["better"] is not None) == real
    assert sum(s["matches"] for s in built["by_outcome"]) == built["matches"]
    assert {s["key"] for s in built["by_outcome"]} <= {"H", "D", "A"}
    assert built["by_season"][0]["label"] == "2007/08"
    assert 0 <= built["all_agree"] <= 1
    assert api_client.get("/api/evaluation/SP1").json() == built  # read from the log since


def test_a_damaged_log_is_explained_in_place(api_client, api_backend):
    log = api_backend.league("SP1").evaluation.log
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("not,a,log\n1,2,3\n", encoding="utf-8")

    answer = api_client.get("/api/evaluation/SP1").json()

    assert answer["has_log"] is True and answer["problem"] and answer["models"] == []


def test_the_leagues_are_compared_once_each_has_its_log(api_client):
    before = api_client.get("/api/leagues-comparison").json()
    assert before["missing"] == ["E0", "SP1"] and before["results"] == []

    built = api_client.post("/api/leagues-comparison/backtest").json()

    assert built["missing"] == [] and built["problem"] is None
    assert [r["code"] for r in built["results"]] == ["E0", "SP1"]
    assert built["matches"] == sum(r["character"]["matches"] for r in built["results"])
    for result in built["results"]:
        character = result["character"]
        assert character["home_win"] + character["draw"] + character["away_win"] == (
            pytest.approx(1)
        )
        assert result["best"] in COMPARED_MODELS
        assert result["brier"][result["best"]] == min(result["brier"][m] for m in COMPARED_MODELS)
        reference = result["brier"][REFERENCE_MODEL]
        for model in COMPARED_MODELS:
            assert result["skill"][model] == pytest.approx(1 - result["brier"][model] / reference)
    assert len(built["pooled"]) == 3
