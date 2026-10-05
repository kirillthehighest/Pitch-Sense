from dataclasses import replace

import pytest

from app.prediction.settings import SETTINGS, league_settings, settings_for, settings_of


def test_every_league_has_calibrated_settings():
    assert set(SETTINGS) == {"E0", "SP1", "I1", "D1", "F1"}


def test_windows_follow_the_size_of_each_league():
    bundesliga, la_liga = settings_for("D1"), settings_for("SP1")

    assert (bundesliga.poisson.league_window, bundesliga.logistic.venue_window) == (306, 17)
    assert (la_liga.poisson.league_window, la_liga.logistic.venue_window) == (380, 19)
    assert settings_for("F1").poisson.league_window == 380  # Ligue 1's usual 20 teams


def test_logistic_regression_uses_the_league_s_own_elo():
    for settings in SETTINGS.values():
        assert settings.logistic.elo == settings.elo


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
