from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from app.evaluation.backtesting import PAST_FREQUENCIES, PredictionLogRow, run_backtest, write_log
from app.evaluation.leagues import (
    MODEL_PAIRS,
    league_character,
    league_results,
    main,
    pooled_differences,
)

SETTINGS = {"first_evaluation_season": "2007-08", "min_training_matches": 3}


def row(season: str, home_goals: int, away_goals: int, day: int) -> PredictionLogRow:
    result = "H" if home_goals > away_goals else "A" if home_goals < away_goals else "D"
    return PredictionLogRow(
        date(2020 if season == "2019-20" else 2021, 1, day), season, "A", "B", home_goals,
        away_goals, result, PAST_FREQUENCIES, 0.5, 0.25, 0.25, "H", None, None, "0", "1",
    )  # fmt: skip


def test_league_character_by_hand():
    rows = [row("2019-20", 2, 0, 1), row("2019-20", 1, 1, 2), row("2020-21", 0, 1, 3)]
    rows.append(row("2020-21", 3, 1, 4))

    character = league_character("SP1", rows)

    assert (character.matches, character.home_win, character.draw, character.away_win) == (
        4, 0.5, 0.25, 0.25,
    )  # fmt: skip
    assert (character.goals, character.home_margin) == (2.25, 0.75)
    assert (character.closed_doors_home_win, character.other_seasons_home_win) == (0.5, 0.5)


def test_league_character_needs_the_closed_doors_season_and_others():
    with pytest.raises(ValueError, match="2020-21"):
        league_character("SP1", [row("2019-20", 2, 0, 1)])


@pytest.fixture
def logs(season_matches, next_season_matches):
    third_season = [
        replace(m, season="2008-09", match_date=m.match_date.replace(year=2008))
        for m in next_season_matches
    ]
    la_liga = [*season_matches, *next_season_matches, *third_season]
    premier = [
        replace(m, competition="E0", home_team="E " + m.home_team, away_team="E " + m.away_team)
        for m in la_liga
    ]
    return {code: run_backtest(matches, **SETTINGS).rows for code, matches in (
        ("SP1", la_liga), ("E0", premier))}  # fmt: skip


def test_skill_is_the_share_of_the_baseline_error_removed(logs):
    results = league_results("SP1", logs["SP1"], closed_doors_season="2008-09")

    brier = {e.model: e.brier.value for e in results.evaluations if e.brier}
    for model, skill in results.skill.items():
        assert skill == pytest.approx(1 - brier[model] / brier[PAST_FREQUENCIES])
    assert results.best == min(results.skill, key=lambda model: brier[model])
    assert [(d.first, d.second) for d in results.differences] == list(MODEL_PAIRS)


def test_pooled_differences_weigh_each_league_by_its_matches(logs):
    per_league = {
        code: league_results(code, rows, "2008-09").differences for code, rows in logs.items()
    }

    pooled = pooled_differences(logs)

    for index, difference in enumerate(pooled):
        parts = [differences[index] for differences in per_league.values()]
        assert difference.matches == sum(part.matches for part in parts)
        weighted = sum(part.mean * part.matches for part in parts) / difference.matches
        assert difference.mean == pytest.approx(weighted)
    assert np.isfinite([d.standard_error for d in pooled]).all()


def test_main_prints_every_league_and_the_pool(logs, tmp_path, capsys):
    for code, rows in logs.items():
        write_log(rows, tmp_path / f"backtest_{code}.csv")

    assert main(["SP1", "E0"], tmp_path, closed_doors_season="2008-09") == 0
    output = capsys.readouterr().out
    assert "La Liga" in output and "Premier League" in output
    assert "All leagues pooled" in output
    assert main(["I1"], tmp_path) == 1
