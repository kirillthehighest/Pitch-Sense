"""The look of the interface: three typefaces, the league's accent and one style sheet.

The application uses Qt's Fusion style everywhere, so macOS and Windows look the same, and its own
dark palette, whatever the system's colour scheme. Widgets are styled through object names and
the ``role`` property, never one by one, so the whole look lives in ``style_sheet``, built from
the palette of the league on screen (``themes.py``, Phase 21).

The look follows the sports apps the team chose as references: neutral, almost black surfaces,
flat cards a step lighter with a hairline edge, generous spacing, round pills for the screens,
chips, filters and tabs, and one accent, the league's, for what is chosen. Plus Jakarta Sans, a
geometric sans, sets the interface in normal case; Barlow Condensed sets only what is read at a
glance (the screen's title, scores, big numbers, team names on a match); Kanit sets the logo.
"""

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from app.data.paths import ASSETS_DIR
from app.ui.themes import DEFAULT_THEME, Theme, set_current_theme

FONT_FAMILY = "Plus Jakarta Sans"
DISPLAY_FAMILY = "Barlow Condensed"
LOGO_FAMILY = "Kanit"
FONTS_DIR = ASSETS_DIR / "fonts"  # static weights, SIL Open Font License (OFL-*.txt)
ICONS_DIR = ASSETS_DIR / "icons"  # the drop-down chevron and the tick of a checkbox
BODY_PIXELS = 14
CARD_RADIUS = 20
BUTTON_RADIUS = 12
PILL_RADIUS = 18
EDGE = "rgba(255, 255, 255, 0.06)"  # the hairline around cards


def _icon(name: str) -> str:
    """A style-sheet reference to a bundled icon (the path may hold spaces and accents)."""
    return f'url("{(ICONS_DIR / name).as_posix()}")'


def style_sheet(theme: Theme) -> str:
    """The style sheet of the whole application in the colours of ``theme``."""
    t = theme
    return f"""
QWidget {{ color: {t.text}; font-family: "{FONT_FAMILY}"; font-size: {BODY_PIXELS}px; }}
QMainWindow, QDialog {{ background: {t.background}; }}
QWidget#page, QStackedWidget#pages, QScrollArea, QScrollArea > QWidget > QWidget,
QWidget#backdrop {{
    background: transparent;
}}
QLabel {{ background: transparent; }}

/* Top bar and side panel */
QFrame#topbar {{ background: {t.night}; border: none; border-bottom: 1px solid {EDGE}; }}
QPushButton[role="nav"] {{
    font-size: 14px; font-weight: 600; color: {t.muted}; background: transparent; border: none;
    border-radius: {PILL_RADIUS}px; padding: 9px 18px;
}}
QPushButton[role="nav"]:hover {{ color: {t.text}; background: {t.surface_high}; }}
QPushButton[role="nav"]:checked {{ color: {t.accent_ink}; background: {t.accent}; }}
QPushButton[role="icon"] {{
    background: {t.surface_high}; color: {t.text}; border: none; border-radius: {PILL_RADIUS}px;
    padding: 9px 16px; font-size: 13px; font-weight: 600;
}}
QPushButton[role="icon"]:hover {{ background: {t.surface_top}; }}
QFrame#sidepanel {{ background: {t.night}; border: none; border-right: 1px solid {EDGE}; }}
QLabel[role="sidebar-note"] {{ color: {t.muted}; font-size: 11px; }}

/* Text */
QLabel[role="title"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 56px; font-weight: 800; color: #FFFFFF;
}}
QLabel[role="subtitle"] {{ color: rgba(255, 255, 255, 0.78); font-size: 14px; }}
QLabel[role="eyebrow"] {{ color: {t.accent_text}; font-size: 12px; font-weight: 700; }}
QLabel[role="hero-eyebrow"] {{ color: #FFFFFF; font-size: 13px; font-weight: 600; }}
QLabel[role="overline"] {{ color: {t.muted}; font-size: 11px; font-weight: 700; }}
QLabel[role="section"] {{ font-size: 18px; font-weight: 700; color: {t.text}; }}
QLabel[role="caption"] {{ color: {t.muted}; font-size: 13px; }}
QLabel[role="credit"] {{ color: rgba(255, 255, 255, 0.62); font-size: 11px; }}
QLabel[role="strong"] {{ color: {t.text}; font-size: 14px; font-weight: 600; }}
QLabel[role="hero"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 40px; font-weight: 700; color: {t.text};
}}
QLabel[role="stat"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 44px; font-weight: 700; color: {t.text};
}}
QLabel[role="score"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 64px; font-weight: 800; color: #FFFFFF;
}}
QLabel[role="team"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 24px; font-weight: 700; color: {t.text};
}}
QLabel[role="status"] {{
    color: {t.accent_ink}; background: {t.accent}; font-size: 12px; font-weight: 700;
    border-radius: 11px; padding: 3px 12px;
}}

/* Cards: flat, a step lighter than the window */
QFrame[role="card"], QFrame[role="favourite"] {{
    background: {t.surface}; border: 1px solid {EDGE}; border-radius: {CARD_RADIUS}px;
}}
QFrame[role="card"] QLabel, QFrame[role="favourite"] QLabel {{ border: none; }}

/* Buttons */
QPushButton {{
    background: {t.surface_high}; color: {t.text}; border: none;
    border-radius: {BUTTON_RADIUS}px; padding: 9px 16px; min-height: 18px; font-weight: 600;
}}
QPushButton:hover {{ background: {t.surface_top}; }}
QPushButton:disabled {{ color: {t.faint}; }}
QPushButton[role="primary"] {{
    background: {t.accent}; color: {t.accent_ink}; font-weight: 700;
}}
QPushButton[role="primary"]:hover {{ background: {t.accent_hover}; }}
QPushButton[role="primary"]:disabled {{ background: {t.surface_top}; color: {t.faint}; }}

/* The matches screen: day chips, arrows, links and filters */
QPushButton[role="chip"] {{
    font-size: 13px; font-weight: 600; color: {t.text}; background: {t.surface};
    border: 1px solid {EDGE}; border-radius: 14px; padding: 7px 4px; min-height: 34px;
}}
QPushButton[role="chip"][empty="true"] {{ color: {t.muted}; background: transparent; }}
QPushButton[role="chip"]:hover {{ background: {t.surface_high}; }}
QPushButton[role="chip"]:checked {{
    background: {t.accent}; border-color: {t.accent}; color: {t.accent_ink}; font-weight: 700;
}}
QPushButton[role="chip-arrow"] {{
    font-size: 18px; font-weight: 600; color: {t.text}; background: {t.surface_high};
    border: none; border-radius: 18px; padding: 0; min-width: 36px; max-width: 36px;
    min-height: 36px; max-height: 36px;
}}
QPushButton[role="chip-arrow"]:hover {{ background: {t.surface_top}; }}
QPushButton[role="link"] {{
    background: transparent; border: none; color: {t.muted}; padding: 2px 2px;
    font-size: 13px; font-weight: 600;
}}
QPushButton[role="link"]:hover {{ color: {t.text}; }}
QPushButton[role="filter"] {{
    background: {t.surface_high}; color: {t.muted}; border: none;
    border-radius: {PILL_RADIUS}px; padding: 8px 16px; min-height: 16px; font-weight: 600;
}}
QPushButton[role="filter"]:hover {{ color: {t.text}; }}
QPushButton[role="filter"]:checked {{ color: {t.night}; background: {t.text}; }}

/* Inputs */
QComboBox, QDateEdit {{
    background: {t.surface_high}; color: {t.text}; border: 1px solid transparent;
    border-radius: {BUTTON_RADIUS}px; padding: 8px 12px; min-height: 18px; font-weight: 500;
}}
QComboBox:hover, QDateEdit:hover {{ background: {t.surface_top}; }}
QComboBox:focus, QDateEdit:focus {{ border-color: {t.rgba("accent", 0.6)}; }}
QComboBox:disabled, QDateEdit:disabled {{ color: {t.faint}; }}
QComboBox::drop-down, QDateEdit::drop-down {{
    subcontrol-origin: padding; subcontrol-position: center right; width: 24px; border: none;
}}
QComboBox::down-arrow, QDateEdit::down-arrow {{
    image: {_icon("chevron-down.svg")}; width: 12px; height: 12px;
}}
QComboBox QAbstractItemView {{
    background: {t.surface_high}; color: {t.text}; border: 1px solid {t.line};
    selection-background-color: {t.surface_top}; selection-color: {t.text}; outline: none;
    padding: 4px;
}}
QCalendarWidget QWidget {{ background: {t.surface_high}; color: {t.text}; }}
QCalendarWidget QToolButton {{ background: transparent; color: {t.text}; border: none; }}
QCalendarWidget QAbstractItemView:enabled {{
    background: {t.surface}; color: {t.text}; selection-background-color: {t.accent};
    selection-color: {t.accent_ink};
}}
QCalendarWidget QAbstractItemView:disabled {{ color: {t.faint}; }}
QRadioButton, QCheckBox {{ spacing: 8px; background: transparent; }}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 14px; height: 14px; border: 2px solid {t.muted}; background: {t.surface_high};
}}
QRadioButton::indicator {{ border-radius: 9px; }}
QRadioButton::indicator:checked {{
    border-color: {t.accent};
    background: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.5, fx: 0.5, fy: 0.5,
        stop: 0 {t.accent}, stop: 0.55 {t.accent}, stop: 0.6 {t.surface_high},
        stop: 1 {t.surface_high});
}}
QCheckBox::indicator {{ border-radius: 5px; }}
QCheckBox::indicator:checked {{
    border-color: {t.accent}; background: {t.accent}; image: {_icon("check.svg")};
}}

/* Tables: rows on the card, hairlines between them */
QTableWidget {{
    background: transparent; color: {t.text}; border: none; gridline-color: {t.line};
    selection-background-color: {t.surface_high}; selection-color: {t.text};
}}
QTableWidget::item {{ border-bottom: 1px solid {EDGE}; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: transparent; color: {t.muted}; border: none; border-bottom: 1px solid {t.line};
    padding: 8px 6px; font-size: 12px; font-weight: 600;
}}
QTableCornerButton::section {{ background: transparent; border: none; }}

/* Tabs inside a page: pills */
QTabWidget::pane {{ border: none; top: -1px; background: transparent; }}
QTabWidget > QStackedWidget > QWidget {{ background: transparent; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    font-size: 13px; font-weight: 600; background: {t.surface_high}; color: {t.muted};
    padding: 8px 16px; margin-right: 8px; border-radius: 16px;
}}
QTabBar::tab:selected {{ color: {t.accent_ink}; background: {t.accent}; }}
QTabBar::tab:hover:!selected {{ color: {t.text}; background: {t.surface_top}; }}

QStatusBar {{ background: {t.night}; color: {t.muted}; border-top: 1px solid {EDGE}; }}
QStatusBar QLabel {{ color: {t.muted}; }}
QToolTip {{
    background: {t.surface_top}; color: {t.text}; border: 1px solid {t.line}; padding: 6px;
    border-radius: 8px;
}}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{
    background: rgba(255, 255, 255, 0.12); border-radius: 3px; min-height: 30px;
}}
QScrollBar::handle:hover {{ background: rgba(255, 255, 255, 0.22); }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


STYLE_SHEET = style_sheet(DEFAULT_THEME)  # the default league's look, before a league is shown


def load_fonts() -> set[str]:
    """Register the bundled typefaces; returns the families that loaded."""
    families: set[str] = set()
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            families.update(QFontDatabase.applicationFontFamilies(font_id))
    return families


def apply_theme(application: QApplication, theme: Theme = DEFAULT_THEME) -> bool:
    """Give the whole application the PitchSense look in the colours of ``theme``; False when a
    bundled typeface did not load and a system font stands in for it.

    Applying the look already on screen (the self-test inside a running application) changes
    nothing, so the restyling of every widget, slow when many exist, is skipped.
    """
    families = load_fonts()
    loaded = {FONT_FAMILY, DISPLAY_FAMILY, LOGO_FAMILY} <= families
    sheet = style_sheet(theme)
    set_current_theme(theme)
    if application.styleSheet() == sheet:
        return loaded
    application.setStyle("Fusion")
    font = QFont(FONT_FAMILY if FONT_FAMILY in families else QFont().family())
    font.setPixelSize(BODY_PIXELS)
    application.setFont(font)
    application.setPalette(qt_palette(theme))
    application.setStyleSheet(sheet)
    return loaded


def apply_window_theme(window: QWidget, theme: Theme) -> None:
    """Give one window, its screens and its dialogs the colours of ``theme`` (a change of league).

    The window's own style sheet overrides the application's; restyling only the window's
    widgets takes a fraction of restyling the whole application (0,14 s against 0,6 s with every
    screen built), so the change of colours starts at once.
    """
    set_current_theme(theme)
    sheet = style_sheet(theme)
    if window.styleSheet() != sheet:
        window.setPalette(qt_palette(theme))
        window.setStyleSheet(sheet)


def qt_palette(theme: Theme) -> QPalette:
    """Qt's own palette in the colours of ``theme``, for what the style sheet does not reach."""
    t = theme
    palette = QPalette()
    for role, colour in (
        (QPalette.ColorRole.Window, t.background),
        (QPalette.ColorRole.Base, t.surface),
        (QPalette.ColorRole.AlternateBase, t.surface_high),
        (QPalette.ColorRole.Text, t.text),
        (QPalette.ColorRole.WindowText, t.text),
        (QPalette.ColorRole.ButtonText, t.text),
        (QPalette.ColorRole.Button, t.surface_high),
        (QPalette.ColorRole.BrightText, t.accent),
        (QPalette.ColorRole.Highlight, t.accent),
        (QPalette.ColorRole.HighlightedText, t.accent_ink),
        (QPalette.ColorRole.PlaceholderText, t.faint),
        (QPalette.ColorRole.ToolTipBase, t.surface_top),
        (QPalette.ColorRole.ToolTipText, t.text),
        (QPalette.ColorRole.Light, t.surface_top),
        (QPalette.ColorRole.Midlight, t.surface_high),
        (QPalette.ColorRole.Mid, t.line),
        (QPalette.ColorRole.Dark, t.night),
        (QPalette.ColorRole.Link, t.accent),
    ):
        palette.setColor(role, QColor(colour))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(t.faint))
    return palette
