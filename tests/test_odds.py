"""The bookmakers' average odds (Phase 23): read from the raw files, stored apart from the
matches, and turned into probabilities with the margin removed proportionally."""

from datetime import date

import pandas as pd
import pytest

from app.data.build_database import build_database
from app.data.loader import load_competition_odds
from app.data.odds import MarketOdds, market_columns, odds_by_match, odds_from_frame
from app.data.preprocessing import DataValidationError
from app.data.repository import MatchRepository


def odds(home=2.0, draw=3.5, away=4.0) -> MarketOdds:
    return MarketOdds("SP1", date(2006, 9, 1), "Alpha", "Bravo", home, draw, away)


def test_the_margin_is_removed_proportionally():
    item = odds(2.0, 4.0, 4.0)  # implied 0.5 + 0.25 + 0.25 = 1: no margin

    assert item.probabilities() == pytest.approx((0.5, 0.25, 0.25))
    home, draw, away = odds(1.8, 3.6, 4.5).probabilities()  # implied sum 1.0556
    assert home + draw + away == pytest.approx(1)
    assert home / draw == pytest.approx(3.6 / 1.8)  # the ratios of the implied ones are kept


@pytest.mark.parametrize("values", [(1.0, 3.0, 4.0), (2.0, 0.5, 4.0), (2.0, 3.0, float("nan"))])
def test_impossible_odds_are_refused(values):
    with pytest.raises(ValueError, match="above 1"):
        odds(*values)


def test_both_families_of_columns_are_read_and_missing_odds_are_left_out():
    base = {"Div": "SP1", "Date": "01/09/2019", "HomeTeam": "Alpha", "AwayTeam": "Bravo"}
    newer = pd.DataFrame(
        [
            {**base, "AvgH": "2.10", "AvgD": "3.30", "AvgA": "3.60"},
            {**base, "HomeTeam": "Charlie", "AvgH": "", "AvgD": "3.30", "AvgA": "3.60"},
        ],
        dtype=str,
    )

    (found,) = odds_from_frame(newer, "2019-20.csv")

    assert (found.home_team, found.home, found.draw, found.away) == ("Alpha", 2.1, 3.3, 3.6)
    assert market_columns(["BbAvH", "BbAvD", "BbAvA"]) == ("BbAvH", "BbAvD", "BbAvA")
    assert market_columns(["B365H", "B365D", "B365A"]) is None
    assert odds_from_frame(pd.DataFrame([base], dtype=str), "no-odds.csv") == []


def test_malformed_odds_are_reported_by_line():
    base = {"Div": "SP1", "Date": "01/09/06", "HomeTeam": "Alpha", "AwayTeam": "Bravo"}
    frame = pd.DataFrame(
        [{**base, "BbAvH": "2,10", "BbAvD": "3.3", "BbAvA": "3.6"}, {**base, "BbAvH": "0.9",
         "BbAvD": "3.3", "BbAvA": "3.6"}],
        dtype=str,
    )  # fmt: skip

    with pytest.raises(DataValidationError, match="line 2.*\\n.*line 3"):
        odds_from_frame(frame, "2006-07.csv")


def test_the_database_keeps_the_odds_of_its_matches(raw_data_dir, tmp_path, four_team_league):
    path = tmp_path / "with-odds.db"

    build_database(raw_data_dir, path, four_team_league)

    with MatchRepository.open(path) as repository:
        stored = repository.market_odds("SP1")
        matches = repository.matches("SP1")
    assert len(stored) == len(matches) == 24
    assert set(odds_by_match(stored)) == {(m.match_date, m.home_team, m.away_team) for m in matches}
    assert stored == sorted(load_competition_odds(raw_data_dir / "SP1"), key=lambda o: o.key)


def test_odds_are_replaced_per_competition(tmp_path):
    with MatchRepository.open(tmp_path / "odds.db") as repository:
        repository.replace_market_odds("SP1", [odds()])
        repository.replace_market_odds("SP1", [odds(home=2.5)])

        assert [item.home for item in repository.market_odds("SP1")] == [2.5]
        assert repository.market_odds("E0") == []
        with pytest.raises(ValueError, match="another competition"):
            repository.replace_market_odds("E0", [odds()])
