from dataclasses import replace
from datetime import date

import pytest

from app.data.models import Match, MatchStatistics, Outcome
from app.prediction.elo_predictions import run_elo
from app.prediction.logistic_features import (
    ELO_GAP,
    EXPECTED_GOALS_DIFFERENCE,
    FEATURE_NAMES,
    build_features,
    feature_names,
)
from app.prediction.poisson_predictions import run_poisson
from app.prediction.settings import EloSettings, LogisticSettings, PoissonSettings, settings_for

POISSON = PoissonSettings(team_window=19, prior_matches=1, league_window=380)
EXTENDED = LogisticSettings(
    0.1, EloSettings(15, 80), 19, 380, (ELO_GAP, EXPECTED_GOALS_DIFFERENCE), POISSON
)


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


# La Liga's calibrated settings with the five base features only
BASE = replace(settings_for("SP1").logistic, extra_features=())


def features_of(matches: list[Match], target: Match) -> tuple[float, ...]:
    return next(f.values for f in build_features(matches, BASE) if f.match == target)


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
    features = build_features(EARLIER, BASE)
    calibrated = build_features(EARLIER)  # La Liga adds both extra features (Phase 23)

    assert [f.match for f in features] == [f.match for f in calibrated] == EARLIER[1:]
    assert all(len(f.values) == len(FEATURE_NAMES) == 5 for f in features)
    assert all(
        len(f.values) == len(feature_names(settings_for("SP1").logistic)) == 7 for f in calibrated
    )


def test_input_order_does_not_matter(season_matches):
    assert build_features(reversed(season_matches)) == build_features(season_matches)


def test_the_extra_features_follow_the_five(season_matches):
    base = {
        f.match: f.values
        for f in build_features(season_matches, replace(EXTENDED, extra_features=()))
    }
    expected = {
        p.match: p.distribution.home_expected_goals - p.distribution.away_expected_goals
        for p in run_poisson(season_matches, POISSON)
    }

    features = build_features(season_matches, EXTENDED)

    assert feature_names(EXTENDED) == (*FEATURE_NAMES, ELO_GAP, EXPECTED_GOALS_DIFFERENCE)
    for f in features:
        assert f.values[:5] == base[f.match]
        assert f.values[5] == abs(f.values[0])
        # On 2 September the league's only match was a 0-1: Poisson has no home goal to use yet,
        # so the league's home minus away goals per match, -1, stands in.
        assert f.values[6] == pytest.approx(expected.get(f.match, -1.0))
    assert len(features) == len(expected) + 1


def test_given_poisson_predictions_give_the_same_features(season_matches):
    computed = build_features(season_matches, EXTENDED)
    given = build_features(season_matches, EXTENDED, poisson=run_poisson(season_matches, POISSON))

    assert given == computed


def test_only_the_chosen_extra_features_are_added(season_matches):
    only_gap = replace(EXTENDED, extra_features=(ELO_GAP,), poisson=None)

    assert feature_names(only_gap) == (*FEATURE_NAMES, ELO_GAP)
    assert all(len(f.values) == 6 for f in build_features(season_matches, only_gap))


def test_before_the_poisson_model_predicts_the_league_goal_difference_stands_in():
    goalless = make(1, "A", "B", 0, 0)
    target = make(2, "C", "D", 1, 1)

    (features,) = build_features([goalless, target], EXTENDED)

    assert features.values[6] == 0.0  # no goals yet: home minus away goals per match is 0


@pytest.mark.parametrize(
    ("extra_features", "poisson", "message"),
    [(("shots",), POISSON, "unknown"), ((EXPECTED_GOALS_DIFFERENCE,), None, "Poisson")],
)
def test_invalid_extra_features_are_rejected(season_matches, extra_features, poisson, message):
    settings = replace(EXTENDED, extra_features=extra_features, poisson=poisson)

    with pytest.raises(ValueError, match=message):
        build_features(season_matches, settings)


@pytest.mark.parametrize("settings", [None, EXTENDED])
def test_changing_a_match_never_changes_features_on_or_before_its_day(season_matches, settings):
    target = season_matches[6]  # 7 September 2006
    changed = replace(
        target,
        home_goals=target.away_goals + 2,
        result=Outcome.HOME_WIN,
        statistics=MatchStatistics(*[9] * 12),
    )

    original = {f.match.match_date: f.values for f in build_features(season_matches, settings)}
    after_change = {
        f.match.match_date: f.values
        for f in build_features([*season_matches[:6], changed, *season_matches[7:]], settings)
    }

    for day in range(2, 8):
        assert original[date(2006, 9, day)] == after_change[date(2006, 9, day)]
    assert any(
        original[date(2006, 9, day)] != after_change[date(2006, 9, day)] for day in range(8, 13)
    )
