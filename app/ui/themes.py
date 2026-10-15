"""The colours of each league (Phase 21): the whole interface takes the palette of the league on
screen, and changing the league repaints it (with the circular reveal of ``transition.py``).

Each palette follows the league's identity: the Premier League's purple, magenta and green, La
Liga's red and orange, Serie A's blues, the Bundesliga's red, Ligue 1's night blue with a lime
accent. Surfaces go from the deepest (``night``) to the highest (``surface_top``); ``accent`` is
the one colour that says "here" (the chosen screen, the primary button, links, "your team");
``glow_primary`` and ``glow_secondary`` light the backdrop, the banner and the logo. The contrast
of every text colour on every surface is checked by ``tests/test_themes.py``.

The colours of match outcomes and of the form guide stay the same in every league
(``app/visualization/palette.py``): they were validated for colour-blind readers.
"""

from dataclasses import dataclass, field

from PySide6.QtGui import QColor


@dataclass(frozen=True, slots=True)
class Theme:
    """One league's palette, as hex colours."""

    code: str
    night: str  # the top bar and the side panel
    background: str  # the window
    surface: str  # cards
    surface_high: str  # headers, inputs, hover
    surface_top: str  # pressed buttons, selected rows
    line: str  # borders and dividers
    text: str
    muted: str  # secondary text
    faint: str  # disabled controls only, never text that must be read
    accent: str
    accent_ink: str  # text on the accent
    glow_primary: str
    glow_secondary: str
    accent_hover: str = field(default="")

    def __post_init__(self) -> None:
        if not self.accent_hover:
            object.__setattr__(self, "accent_hover", QColor(self.accent).lighter(118).name())

    @property
    def accent_tint(self) -> str:
        """The accent at 16% over a card: the row of "your team"."""
        return blend(self.surface, self.accent, 0.16)

    def rgba(self, name: str, alpha: float) -> str:
        """A colour of the palette with an opacity, for the style sheet: rgba(r, g, b, a)."""
        colour = QColor(getattr(self, name))
        return f"rgba({colour.red()}, {colour.green()}, {colour.blue()}, {alpha:.2f})"


def blend(first: str, second: str, share: float) -> str:
    """The colour ``share`` of the way from ``first`` to ``second``."""
    a, b = QColor(first), QColor(second)
    mix = (
        round(a.red() + (b.red() - a.red()) * share),
        round(a.green() + (b.green() - a.green()) * share),
        round(a.blue() + (b.blue() - a.blue()) * share),
    )
    return QColor(*mix).name()


THEMES = {
    "E0": Theme(
        code="E0",
        night="#12051F",
        background="#180A28",
        surface="#231236",
        surface_high="#2E1945",
        surface_top="#3A2156",
        line="#4A2C6A",
        text="#F6F1FB",
        muted="#BBAAD2",
        faint="#7D6A96",
        accent="#00FF85",
        accent_ink="#12051F",
        glow_primary="#E90052",
        glow_secondary="#7B2FF7",
    ),
    "SP1": Theme(
        code="SP1",
        night="#160705",
        background="#1D0A07",
        surface="#2A110D",
        surface_high="#381812",
        surface_top="#47201A",
        line="#5C2B22",
        text="#FCF4F1",
        muted="#D2B1A7",
        faint="#8E6F66",
        accent="#FF8A3D",
        accent_ink="#160705",
        glow_primary="#FF3B30",
        glow_secondary="#FF9500",
    ),
    "I1": Theme(
        code="I1",
        night="#040B1D",
        background="#071229",
        surface="#0C1C3C",
        surface_high="#12274E",
        surface_top="#193262",
        line="#22417A",
        text="#F1F6FD",
        muted="#A8BADB",
        faint="#6A7C9E",
        accent="#3DDCFF",
        accent_ink="#040B1D",
        glow_primary="#1F5BFF",
        glow_secondary="#00C8FF",
    ),
    "D1": Theme(
        code="D1",
        night="#150406",
        background="#1C0608",
        surface="#290B0F",
        surface_high="#371116",
        surface_top="#46171E",
        line="#5C2029",
        text="#FCF2F3",
        muted="#D7ACB2",
        faint="#946A70",
        accent="#FF5566",
        accent_ink="#150406",
        glow_primary="#D20515",
        glow_secondary="#FF7A85",
    ),
    "F1": Theme(
        code="F1",
        night="#05080F",
        background="#080D19",
        surface="#0E1526",
        surface_high="#151F36",
        surface_top="#1C2946",
        line="#28385C",
        text="#F2F5FA",
        muted="#AAB5CC",
        faint="#6B7798",
        accent="#D4FF3D",
        accent_ink="#05080F",
        glow_primary="#2A4BFF",
        glow_secondary="#00A3FF",
    ),
}
DEFAULT_THEME = THEMES["SP1"]  # the default league's; also the colours of the package icons

_current = DEFAULT_THEME


def theme_for(code: str) -> Theme:
    """The palette of a league; a league without one gets the default palette."""
    return THEMES.get(code, DEFAULT_THEME)


def current_theme() -> Theme:
    """The palette on screen; painted widgets read it every time they paint."""
    return _current


def set_current_theme(theme: Theme) -> None:
    """Make ``theme`` the palette on screen (``apply_theme`` calls it)."""
    global _current
    _current = theme
