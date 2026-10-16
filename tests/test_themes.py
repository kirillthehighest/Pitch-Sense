"""The palettes of the leagues (Phase 21): neutral surfaces shared by every league, one accent per
league, and every text readable on every surface it is written on."""

import pytest
from PySide6.QtGui import QColor

from app.data.competitions import COMPETITIONS
from app.services.images import photo_top
from app.ui.brand import league_photo
from app.ui.theme import STYLE_SHEET, style_sheet
from app.ui.themes import DEFAULT_THEME, THEMES, blend, theme_for
from app.ui.widgets import ProbabilityBars, edge_colour
from app.visualization.palette import FORM_DRAW, LOSS, NIGHT, WIN

HEAD_LIGHT = 235 / 255  # the league colour at the top of a match's or a team's head


def contrast(foreground: str, background: str) -> float:
    """The WCAG contrast ratio of two colours."""

    def luminance(colour: str) -> float:
        channels = [value / 255 for value in QColor(colour).getRgb()[:3]]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def surfaces(theme) -> list[str]:
    return [theme.night, theme.background, theme.surface, theme.surface_high, theme.surface_top]


def test_every_league_has_its_own_accent_on_the_same_surfaces():
    assert set(THEMES) == set(COMPETITIONS)
    assert len({theme.accent for theme in THEMES.values()}) == len(THEMES)
    assert len({theme.brand for theme in THEMES.values()}) == len(THEMES)
    assert len({tuple(surfaces(theme)) for theme in THEMES.values()}) == 1  # neutral, shared
    assert all(theme_for(code).code == code for code in COMPETITIONS)
    assert theme_for("XX") is DEFAULT_THEME


@pytest.mark.parametrize("code", sorted(THEMES))
def test_text_is_readable_on_every_surface(code):
    theme = THEMES[code]
    for surface in surfaces(theme):
        assert contrast(theme.text, surface) >= 7, surface  # WCAG AAA for body text
        assert contrast(theme.muted, surface) >= 4.5, surface  # AA for secondary text
    assert contrast(theme.text, theme.accent_tint) >= 7  # the row of "your team"


@pytest.mark.parametrize("code", sorted(THEMES))
def test_the_accent_is_readable_as_text_and_carries_readable_text(code):
    theme = THEMES[code]
    for surface in surfaces(theme)[:4]:
        assert contrast(theme.accent_text, surface) >= 4.5  # times, links, "your team"
    assert contrast(theme.accent_ink, theme.accent) >= 4.5  # the chosen screen, primary buttons
    assert contrast(theme.accent_ink, theme.accent_hover) >= 4.5


@pytest.mark.parametrize("code", sorted(THEMES))
def test_white_text_is_readable_on_the_league_colours(code):
    theme = THEMES[code]
    head = blend(theme.surface, theme.brand, HEAD_LIGHT)  # the top of a match's or team's head
    assert contrast("#FFFFFF", head) >= 4.5
    assert contrast("#FFFFFF", theme.brand) >= 4.5  # the banner without an image
    photo = league_photo(code)
    fill = blend(edge_colour(photo, photo_top(code)), theme.brand, 0.5)  # the banner's fill
    assert contrast("#FFFFFF", fill) >= 4.5


@pytest.mark.parametrize("code", sorted(THEMES))
def test_the_probability_bars_carry_readable_percentages(code, monkeypatch):
    monkeypatch.setattr("app.ui.widgets.current_theme", lambda: THEMES[code])
    for fill, ink in ProbabilityBars.colours():
        assert contrast(ink, fill) >= 4.5


@pytest.mark.parametrize("fill", [WIN, FORM_DRAW, LOSS])
def test_the_form_squares_carry_readable_letters(fill):
    assert contrast("#FFFFFF", fill) >= 4.5
    assert NIGHT != fill


@pytest.mark.parametrize("code", sorted(THEMES))
def test_the_style_sheet_is_drawn_in_the_league_colours(code):
    theme = THEMES[code]
    sheet = style_sheet(theme)

    assert f"color: {theme.accent_ink}; background: {theme.accent};" in sheet  # the chosen screen
    assert f"background: {theme.accent}; color: {theme.accent_ink};" in sheet  # primary buttons
    others = {other.accent for other in THEMES.values() if other is not theme}
    assert not any(accent in sheet for accent in others)
    assert STYLE_SHEET == style_sheet(DEFAULT_THEME)


def test_blending_goes_from_one_colour_to_the_other():
    assert blend("#000000", "#FFFFFF", 0) == "#000000"
    assert blend("#000000", "#FFFFFF", 1) == "#ffffff"
    assert blend("#000000", "#FF8000", 0.5) == "#804000"
    assert THEMES["E0"].rgba("accent", 0.5) == "rgba(0, 255, 133, 0.50)"
