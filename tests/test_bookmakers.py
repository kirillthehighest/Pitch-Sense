"""The models measured against the bookmakers (Phase 23), on the synthetic seasons."""

import pytest

from app.data.odds import odds_by_match
from app.data.repository import MatchRepository
from app.evaluation.backtesting import PAST_FREQUENCIES, run_backtest
from app.evaluation.bookmakers import BOOKMAKERS, bookmaker_rows, compare_with_bookmakers, main
from app.evaluation.comparison import COMPARED_MODELS, Measure


@pytest.fixture
def stored(database):
    with MatchRepository.open(database) as repository:
        return repository.matches("SP1"), repository.market_odds("SP1")


@pytest.fixture
def log(stored):
    matches, _ = stored
    backtest = run_backtest(matches, first_evaluation_season="2007-08", min_training_matches=3)
    return list(backtest.rows)


def test_the_bookmakers_forecast_is_the_odds_without_their_margin(log, stored):
    _, odds = stored
    by_match = odds_by_match(odds)

    rows = bookmaker_rows(log, by_match)

    assert len(rows) == 12  # one per evaluation match, whatever the number of models
    for row in rows:
        item = by_match[(row.match_date, row.home_team, row.away_team)]
        assert (row.p_home, row.p_draw, row.p_away) == pytest.approx(item.probabilities())
        assert row.model == BOOKMAKERS and row.expected_home_goals is None


def test_the_models_are_compared_with_the_bookmakers_on_the_same_matches(log, stored):
    _, odds = stored

    result = compare_with_bookmakers("SP1", log, odds)

    assert (result.matches, result.missing) == (12, 0)
    assert [e.model for e in result.evaluations][-1] == BOOKMAKERS
    assert {e.matches for e in result.evaluations} == {12}
    assert result.bookmakers.brier is not None and len(result.bookmakers.confident) == 4
    assert [d.first for d in result.differences] == [*COMPARED_MODELS, PAST_FREQUENCIES]
    assert {d.second for d in result.differences} == {BOOKMAKERS}
    assert {d.measure for d in result.differences} == {Measure.BRIER}


def test_matches_without_odds_are_left_out_and_counted(log, stored):
    _, odds = stored

    result = compare_with_bookmakers("SP1", log, odds[:-3])  # the last three have none

    assert (result.matches, result.missing) == (9, 3)
    assert compare_with_bookmakers("SP1", log, []) is None


def test_the_command_explains_a_missing_database(tmp_path, capsys):
    assert main(["SP1"], tmp_path / "missing.db") == 1
    assert "python -m app.data.build_database" in capsys.readouterr().err
