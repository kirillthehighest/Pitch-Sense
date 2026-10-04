from dataclasses import replace
from datetime import date

import pytest

from app.data.models import Match, MatchStatistics, Outcome
from app.prediction.elo_predictions import run_elo
from app.prediction.logistic_features import FEATURE_NAMES, build_features


def make(
    day: int,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    shots_on_target: tuple[int, int] | None = None,
) -> Match:
    statistics = None
    if shots_on_target is not None:
        home_target, away_target = shots_on_target
        statistics = MatchStatistics(10, 10, home_target, away_target, 0, 0, 0, 0, 0, 0, 0, 0)
    return Match(
        competition="SP1",
        season="2006-07",
        match_date=date(2006, 9, day),
        home_team=home_team,
        away_team=away_team,
        home_goals=home_goals,
        away_goals=away_goals,
        result=Outcome.from_score(home_goals, away_goals),
        statistics=statistics,
    )


# League before 5 September: results H, D, A, H; goals 6-4; shots on target recorded twice.
EARLIER = [
    make(1, "A", "B", 2, 1, shots_on_target=(6, 2)),
    make(2, "C", "D", 1, 1),
    make(3, "B", "C", 0, 2, shots_on_target=(1, 3)),
    make(4, "D", "A", 3, 0),
]


def features_of(matches: list[Match], target: Match) -> tuple[float, ...]:
    return next(f.values for f in build_features(matches) if f.match == target)


def elo_difference(matches: list[Match], target: Match) -> float:
    prediction = next(p for p in run_elo(matches).predictions if p.match == target)
    return prediction.home_rating - prediction.away_rating


def test_hand_computed_features():
    target = make(5, "A", "C", 1, 1)
    matches = [*EARLIER, target]

    values = features_of(matches, target)

    # A at home: one win 2-1 (3 points, +1), shots on target 6 - 2 = +4.
    # C away: one win 2-0 (3 points, +2), shots on target 3 - 1 = +2.
    # Form (last 5, any venue): A won and lost (1.5 points per match), C drew and won (2.0).
    assert values[0] == pytest.approx(elo_difference(matches, target))
    assert values[1:] == pytest.approx((3 - 3, 1 - 2, 1.5 - 2.0, 4 - 2))


def test_league_averages_stand_in_for_a_team_without_history():
    target = make(5, "E", "A", 0, 0)  # E has never played

    values = features_of([*EARLIER, target], target)

    # League: home points per match 3 * 1/2 + 1/4 = 1.75, overall (3 - 1/4) / 2 = 1.375,
    # home goal difference (6 - 4) / 4 = +0.5, home shots-on-target difference (4 - 2) / 2 = +1.
    # A away: lost 0-3 (0 points, -3) without recorded statistics, so it gets the away average -1.
    # A's form: a win and a loss, 1.5 points per match.
    assert values[1:] == pytest.approx((1.75 - 0.0, 0.5 - (-3.0), 1.375 - 1.5, 1.0 - (-1.0)))


def test_every_match_after_the_first_day_has_all_features():
    features = build_features(EARLIER)

    assert [f.match for f in features] == EARLIER[1:]
    assert all(len(f.values) == len(FEATURE_NAMES) == 5 for f in features)


def test_input_order_does_not_matter(season_matches):
    assert build_features(reversed(season_matches)) == build_features(season_matches)


def test_changing_a_match_never_changes_features_on_or_before_its_day(season_matches):
    target = season_matches[6]  # 7 September 2006
    changed = replace(
        target,
        home_goals=target.away_goals + 2,
        result=Outcome.HOME_WIN,
        statistics=MatchStatistics(*[9] * 12),
    )

    original = {f.match.match_date: f.values for f in build_features(season_matches)}
    after_change = {
        f.match.match_date: f.values
        for f in build_features([*season_matches[:6], changed, *season_matches[7:]])
    }

    for day in range(2, 8):
        assert original[date(2006, 9, day)] == after_change[date(2006, 9, day)]
    assert any(
        original[date(2006, 9, day)] != after_change[date(2006, 9, day)] for day in range(8, 13)
    )
