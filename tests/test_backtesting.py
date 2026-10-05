import pytest

from app.data.build_database import build_database
from app.evaluation.backtesting import (
    ALWAYS_HOME_WIN,
    MODEL_ORDER,
    PAST_FREQUENCIES,
    main,
    read_log,
    run_backtest,
    write_log,
)
from app.evaluation.team_clustering import point_in_time_groups
from app.prediction.outputs import ModelName
from app.statistics.team_statistics import MatchHistory

SETTINGS = {"first_evaluation_season": "2007-08", "min_training_matches": 3}


@pytest.fixture
def two_seasons(season_matches, next_season_matches):
    return [*season_matches, *next_season_matches]


@pytest.fixture
def backtest(two_seasons):
    return run_backtest(two_seasons, **SETTINGS)


def test_every_evaluation_match_has_one_row_per_model(backtest):
    rows = backtest.rows

    assert backtest.excluded_matches == 0
    assert len(rows) == 12 * len(MODEL_ORDER)
    assert {row.season for row in rows} == {"2007-08"}
    assert [row.model for row in rows[: len(MODEL_ORDER)]] == list(MODEL_ORDER)


def test_rows_hold_valid_forecasts_and_the_real_result(backtest):
    for row in backtest.rows:
        probabilities = (row.p_home, row.p_draw, row.p_away)
        assert min(probabilities) >= 0
        assert sum(probabilities) == pytest.approx(1)
        assert row.predicted == "HDA"[probabilities.index(max(probabilities))]
        expected = (
            "H"
            if row.home_goals > row.away_goals
            else "A"
            if row.home_goals < row.away_goals
            else "D"
        )
        assert row.actual == expected


def test_only_poisson_rows_carry_expected_goals(backtest):
    for row in backtest.rows:
        has_goals = row.expected_home_goals is not None and row.expected_away_goals is not None
        assert has_goals == (row.model == ModelName.POISSON)


def test_baselines(backtest):
    home_win = [row for row in backtest.rows if row.model == ALWAYS_HOME_WIN]
    first_frequencies = next(row for row in backtest.rows if row.model == PAST_FREQUENCIES)

    assert all(
        (r.p_home, r.p_draw, r.p_away, r.predicted) == (1.0, 0.0, 0.0, "H") for r in home_win
    )
    # Before the first 2007-08 match the league has the 12 matches of 2006-07:
    # 6 home wins, 4 draws and 2 away wins.
    assert (
        first_frequencies.p_home,
        first_frequencies.p_draw,
        first_frequencies.p_away,
    ) == pytest.approx((6 / 12, 4 / 12, 2 / 12))


def test_rows_carry_the_point_in_time_groups(backtest, two_seasons):
    groups = point_in_time_groups(MatchHistory(two_seasons), "2007-08")

    for row in backtest.rows:
        assert row.home_group == str(groups[row.home_team])
        assert row.away_group == str(groups[row.away_team])


def test_matches_without_every_model_are_left_out(two_seasons):
    backtest = run_backtest(two_seasons, first_evaluation_season="2007-08", min_training_matches=20)

    logged_matches = len(backtest.rows) // len(MODEL_ORDER)
    assert backtest.excluded_matches > 0
    assert logged_matches + backtest.excluded_matches == 12


def test_the_backtest_is_reproducible(two_seasons, backtest):
    assert run_backtest(two_seasons, **SETTINGS) == backtest


def test_the_log_survives_saving_and_loading(backtest, tmp_path):
    path = tmp_path / "results" / "backtest.csv"

    write_log(backtest.rows, path)

    assert read_log(path) == list(backtest.rows)


def damaged(backtest, tmp_path, change):
    """Write the log, then let ``change`` alter its lines."""
    path = tmp_path / "backtest.csv"
    write_log(backtest.rows, path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text("".join(change(lines)), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda lines: [], "backtest.csv is empty"),
        (lambda lines: ["date,model\n", "2007-09-01,Elo\n"], "not a prediction log: missing"),
        (lambda lines: [*lines[:3], lines[3][:40]], "line 4: expected 16 values"),
        (
            lambda lines: [*lines[:2], lines[2].rstrip("\r\n") + ",extra\r\n"],
            "line 3: expected 16 values",
        ),
        (
            lambda lines: [lines[0], lines[1].replace(",Elo,", ",Elo,abc", 1), *lines[2:]],
            "line 2: could not convert string to float",
        ),
    ],
    ids=["empty", "other file", "cut-off row", "extra value", "bad number"],
)
def test_a_damaged_log_is_refused_with_its_line(backtest, tmp_path, change, message):
    path = damaged(backtest, tmp_path, change)

    with pytest.raises(ValueError, match=message):
        read_log(path)


def test_the_first_season_cannot_be_evaluated(two_seasons):
    with pytest.raises(ValueError, match="no completed season before"):
        run_backtest(two_seasons, first_evaluation_season="2006-07", min_training_matches=3)


def test_main_writes_the_log(raw_data_dir, tmp_path, capsys):
    database_path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, database_path, {"SP1": 4})
    output = tmp_path / "log.csv"

    exit_code = main(database_path, output, **SETTINGS)

    assert exit_code == 0
    assert len(read_log(output)) == 12 * len(MODEL_ORDER)
    assert "12 matches" in capsys.readouterr().out


def test_main_explains_problems(tmp_path, capsys):
    assert main(tmp_path / "missing.db") == 1
    assert "python -m app.data.build_database" in capsys.readouterr().err
