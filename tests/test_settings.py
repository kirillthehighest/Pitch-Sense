from dataclasses import replace

import pytest

from app.data.competitions import competition
from app.prediction.settings import SETTINGS, league_settings, settings_for, settings_of
from app.services.explanations import EXPLANATIONS


def test_every_league_has_calibrated_settings():
    assert set(SETTINGS) == {"E0", "SP1", "I1", "D1", "F1"}


def test_windows_follow_the_size_of_each_league():
    bundesliga, la_liga = settings_for("D1"), settings_for("SP1")

    assert (bundesliga.poisson.league_window, bundesliga.logistic.venue_window) == (306, 17)
    assert (la_liga.poisson.league_window, la_liga.logistic.venue_window) == (380, 19)
    assert settings_for("F1").poisson.league_window == 380  # Ligue 1's usual 20 teams


def test_logistic_regression_uses_the_league_s_own_elo_and_poisson():
    for settings in SETTINGS.values():
        assert settings.logistic.elo == settings.elo
        assert settings.logistic.poisson == settings.poisson


def test_the_phase_23_options_reach_each_model():
    settings = league_settings(
        "SP1",
        10,
        80,
        76,
        10,
        0.1,
        goal_margin=True,
        half_life=19,
        rho=-0.04,
        extra_features=("elo_gap",),
    )

    assert settings.elo.goal_margin is True
    assert (settings.poisson.half_life, settings.poisson.rho) == (19, -0.04)
    assert settings.logistic.extra_features == ("elo_gap",)
    plain = league_settings("SP1", 10, 80, 76, 10, 0.1)
    assert (plain.elo.goal_margin, plain.poisson.half_life, plain.poisson.rho) == (False, None, 0)
    assert plain.logistic.extra_features == ()


def test_settings_combine_calibrated_values_with_the_league_windows():
    settings = league_settings("D1", 15, 60, 51, 20, 0.1)

    assert (settings.elo.k_factor, settings.elo.home_advantage) == (15, 60)
    assert (settings.poisson.team_window, settings.poisson.prior_matches) == (51, 20)
    assert settings.logistic.l2 == 0.1


def test_unknown_and_mixed_competitions_are_errors(season_matches):
    with pytest.raises(ValueError, match="no calibrated settings"):
        settings_for("XX")
    with pytest.raises(ValueError, match="one competition"):
        settings_of([*season_matches, replace(season_matches[0], competition="E0")])
    assert settings_of(season_matches) == settings_for("SP1")


def test_the_analysis_text_names_the_leagues_of_each_phase_23_option():
    # app/services/explanations.py tells which leagues use each option the calibration chose
    texts = dict(EXPLANATIONS)
    names = {code: competition(code).name for code in SETTINGS}

    def leagues(chosen) -> set[str]:
        return {names[code] for code, settings in SETTINGS.items() if chosen(settings)}

    margin = leagues(lambda s: s.elo.goal_margin)
    assert margin == {"Premier League", "La Liga", "Bundesliga"}
    assert all(name in texts["Ratingul Elo"] for name in margin)
    assert leagues(lambda s: s.poisson.half_life is None) == {"Serie A"}
    assert "Serie A" in texts["Modelul Poisson"]
    assert all(s.poisson.rho < 0 for s in SETTINGS.values())  # Dixon-Coles in every league
    expected_goals = leagues(lambda s: "expected_goals_difference" in s.logistic.extra_features)
    assert expected_goals == {"Premier League", "La Liga", "Serie A"}
    assert leagues(lambda s: "elo_gap" in s.logistic.extra_features) == {"La Liga"}
    assert all(name in texts["Regresia logistică"] for name in expected_goals)
