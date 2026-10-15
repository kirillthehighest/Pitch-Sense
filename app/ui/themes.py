"""The colours of each league (Phase 21): the interface takes the accent of the league on screen,
and changing the league repaints it (with the reveal of ``transition.py``).

The surfaces are the same for every league: a neutral, almost black night, with cards a step
lighter, as in the sports apps the team chose as references (Sportia, LiveScore, OneFootball).
A league's identity lives only in a few places, so it never tints the whole screen: the accent
(the chosen screen and league, the primary button, the most likely outcome, "your team"), the
banner with the league's image, and the lower half of the logo. ``accent`` fills shapes and carries
``accent_ink``; ``accent_text`` is the accent written on the dark surfaces, lighter where the
fill would be too dark to read; ``brand`` is the league's own deep colour, behind the banner when
there is no image. The contrast of every text colour on every surface is checked by
``tests/test_themes.py``.

The colours of match outcomes and of the form guide stay the same in every league
(``app/visualization/palette.py``): they were validated for colour-blind readers.
"""

from dataclasses import dataclass, field

from PySide6.QtGui import QColor


@dataclass(frozen=True, slots=True)
class Theme:
    """One league's palette, as hex colours; the surfaces are shared by all leagues."""

    code: str
    accent: str
    accent_ink: str  # text on the accent
    accent_text: str  # the accent as text or a thin line on the dark surfaces
    brand: str  # the league's deep colour: the banner without an image
    night: str = "#0A0A0C"  # the top bar and the side panel
    background: str = "#0E0E11"  # the window
    surface: str = "#16161A"  # cards
    surface_high: str = "#1E1E23"  # chips, inputs, the heads of lists, buttons
    surface_top: str = "#28282E"  # hover and pressed
    line: str = "#2A2A30"  # hairlines between rows
    text: str = "#F5F5F7"
    muted: str = "#9C9CA6"  # secondary text
    faint: str = "#5E5E68"  # disabled controls only, never text that must be read
    accent_hover: str = field(default="")

    def __post_init__(self) -> None:
        if not self.accent_hover:  # lighter on hover, under dark text
            object.__setattr__(self, "accent_hover", QColor(self.accent).lighter(112).name())

    @property
    def accent_tint(self) -> str:
        """The accent at 14% over a card: the row of "your team"."""
        return blend(self.surface, self.accent, 0.14)

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
    # The Premier League's green over its purple
    "E0": Theme(
        code="E0", accent="#00FF85", accent_ink="#0A0A0C", accent_text="#00FF85", brand="#37003C"
    ),
    # La Liga's orange over its red
    "SP1": Theme(
        code="SP1", accent="#FF7A3D", accent_ink="#0A0A0C", accent_text="#FF8B55", brand="#6E140E"
    ),
    # Serie A's cyan over its blue
    "I1": Theme(
        code="I1", accent="#3DDCFF", accent_ink="#0A0A0C", accent_text="#3DDCFF", brand="#0B2A6F"
    ),
    # The Bundesliga's red, written lighter on the dark
    "D1": Theme(
        code="D1",
        accent="#E2001A",
        accent_ink="#FFFFFF",
        accent_text="#FF5A6A",
        brand="#7A0410",
        accent_hover="#C70017",  # darker on hover: its text is white
    ),
    # Ligue 1's lime over its night blue
    "F1": Theme(
        code="F1", accent="#D4FF3D", accent_ink="#0A0A0C", accent_text="#D4FF3D", brand="#0E1D45"
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
