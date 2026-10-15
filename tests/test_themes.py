"""The palettes of the leagues (Phase 21): one per league, and every text readable on every
surface it is written on, including the glass cards over the backdrop's glows."""

import pytest
from PySide6.QtGui import QColor

from app.data.competitions import COMPETITIONS
from app.ui.theme import STYLE_SHEET, style_sheet
from app.ui.themes import DEFAULT_THEME, THEMES, blend, theme_for
from app.visualization.palette import AWAY, DRAW, FORM_DRAW, HOME, LOSS, NIGHT, WIN

GLASS = 0.74  # the cards' opacity over the backdrop (theme.py)
BACKDROP_GLOW = 70 / 255  # the strongest glow of the backdrop (widgets.Backdrop)
CARD_GLOW = 120 / 255  # the glows of a match's or a team's head (widgets.paint_league_card)


def contrast(foreground: str, background: str) -> float:
    """The WCAG contrast ratio of two colours."""

    def luminance(colour: str) -> float:
        channels = [value / 255 for value in QColor(colour).getRgb()[:3]]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def surfaces(theme) -> dict[str, str]:
    """Every colour text is written on, the glass cards at the brightest point of a glow."""
    glows = {
        f"glass over {name}": blend(
            blend(theme.background, glow, BACKDROP_GLOW), theme.surface, GLASS
        )
        for name, glow in (
            ("glow_primary", theme.glow_primary),
            ("glow_secondary", theme.glow_secondary),
        )
    }
    return {
        "night": theme.night,
        "background": theme.background,
        "surface": theme.surface,
        "surface_high": theme.surface_high,
        "surface_top": theme.surface_top,
        **glows,
    }


def test_every_league_has_its_own_palette():
    assert set(THEMES) == set(COMPETITIONS)
    assert len({theme.accent for theme in THEMES.values()}) == len(THEMES)
    assert len({theme.surface for theme in THEMES.values()}) == len(THEMES)
    assert all(theme_for(code).code == code for code in COMPETITIONS)
    assert theme_for("XX") is DEFAULT_THEME


@pytest.mark.parametrize("code", sorted(THEMES))
def test_text_is_readable_on_every_surface(code):
    theme = THEMES[code]
    for name, surface in surfaces(theme).items():
        assert contrast(theme.text, surface) >= 7, name  # WCAG AAA for body text
        assert contrast(theme.muted, surface) >= 4.5, name  # AA for secondary text
    assert contrast(theme.text, theme.accent_tint) >= 7  # the row of "your team"


@pytest.mark.parametrize("code", sorted(THEMES))
def test_the_accent_is_readable_as_text_and_carries_readable_text(code):
    theme = THEMES[code]
    for surface in (theme.night, theme.background, theme.surface, theme.surface_high):
        assert contrast(theme.accent, surface) >= 4.5  # links, eyebrows, "your team"
    assert contrast(theme.accent_ink, theme.accent) >= 4.5  # the chosen screen, primary buttons
    assert contrast(theme.accent_ink, theme.accent_hover) >= 4.5


@pytest.mark.parametrize("code", sorted(THEMES))
def test_white_text_is_readable_on_the_heads_of_matches_and_teams(code):
    theme = THEMES[code]
    for glow in (theme.glow_primary, theme.glow_secondary):
        for base in (theme.surface_high, theme.night):
            assert contrast("#FFFFFF", blend(base, glow, CARD_GLOW)) >= 4.5


@pytest.mark.parametrize(
    ("text", "background"),
    [(NIGHT, DRAW)] + [("#FFFFFF", colour) for colour in (HOME, AWAY, WIN, FORM_DRAW, LOSS)],
)
def test_the_outcome_colours_carry_readable_labels_in_every_league(text, background):
    assert contrast(text, background) >= 4.5


@pytest.mark.parametrize("code", sorted(THEMES))
def test_the_style_sheet_is_drawn_in_the_league_colours(code):
    theme = THEMES[code]
    sheet = style_sheet(theme)

    assert f"color: {theme.accent_ink}; background: {theme.accent};" in sheet  # the chosen screen
    assert f"background: {theme.accent}; color: {theme.accent_ink};" in sheet  # primary buttons
    assert theme.rgba("surface", GLASS) in sheet  # glass cards
    others = {other.accent for other in THEMES.values() if other is not theme}
    assert not any(accent in sheet for accent in others)
    assert STYLE_SHEET == style_sheet(DEFAULT_THEME)


def test_blending_goes_from_one_colour_to_the_other():
    assert blend("#000000", "#FFFFFF", 0) == "#000000"
    assert blend("#000000", "#FFFFFF", 1) == "#ffffff"
    assert blend("#000000", "#FF8000", 0.5) == "#804000"
    assert THEMES["E0"].rgba("accent", 0.5) == "rgba(0, 255, 133, 0.50)"
