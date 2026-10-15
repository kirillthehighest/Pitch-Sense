"""The look of the interface: three typefaces, the league's palette and one style sheet.

The application uses Qt's Fusion style everywhere, so macOS and Windows look the same, and its own
dark palette, whatever the system's colour scheme. Widgets are styled through object names and
the ``role`` property, never one by one, so the whole look lives in ``style_sheet``, built from
the palette of the league on screen (``themes.py``, Phase 21). The style is "dark glass": cards
let the lit backdrop show through, corners are round, and buttons, screens, chips and tabs are
pills, the chosen one filled with the league's accent.

Libre Franklin sets the text; Barlow Condensed, a condensed sports face, sets titles, numbers and
the navigation, always in capitals; Kanit's heavy italics set the logo and the wordmark.
"""

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from app.data.paths import ASSETS_DIR
from app.ui.themes import DEFAULT_THEME, Theme, set_current_theme

FONT_FAMILY = "Libre Franklin"
DISPLAY_FAMILY = "Barlow Condensed"
LOGO_FAMILY = "Kanit"
FONTS_DIR = ASSETS_DIR / "fonts"  # static weights, SIL Open Font License (OFL-*.txt)
ICONS_DIR = ASSETS_DIR / "icons"  # the drop-down chevron and the tick of a checkbox
BODY_PIXELS = 14
CARD_RADIUS = 20
PILL_RADIUS = 18


def _icon(name: str) -> str:
    """A style-sheet reference to a bundled icon (the path may hold spaces and accents)."""
    return f'url("{(ICONS_DIR / name).as_posix()}")'


def style_sheet(theme: Theme) -> str:
    """The style sheet of the whole application in the colours of ``theme``."""
    t = theme
    glass = t.rgba("surface", 0.74)
    edge = "rgba(255, 255, 255, 0.08)"
    return f"""
QWidget {{ color: {t.text}; font-family: "{FONT_FAMILY}"; font-size: {BODY_PIXELS}px; }}
QMainWindow, QDialog {{ background: {t.background}; }}
QWidget#page, QStackedWidget#pages, QScrollArea, QScrollArea > QWidget > QWidget,
QWidget#backdrop {{
    background: transparent;
}}
QLabel {{ background: transparent; }}

/* Top bar and side panel */
QFrame#topbar {{ background: {t.rgba("night", 0.82)}; border: none; }}
QPushButton[role="nav"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 17px; font-weight: 700; color: {t.muted};
    background: transparent; border: none; border-radius: {PILL_RADIUS}px; padding: 7px 18px;
}}
QPushButton[role="nav"]:hover {{ color: {t.text}; background: {t.rgba("surface_high", 0.8)}; }}
QPushButton[role="nav"]:checked {{ color: {t.accent_ink}; background: {t.accent}; }}
QPushButton[role="favourite"] {{
    background: transparent; color: {t.accent}; border: 1px solid {t.accent};
    border-radius: {PILL_RADIUS}px; padding: 7px 18px; min-height: 18px; font-weight: 700;
}}
QPushButton[role="favourite"]:hover {{ background: {t.accent}; color: {t.accent_ink}; }}
QFrame#sidepanel {{
    background: {t.rgba("night", 0.72)}; border: none; border-right: 1px solid {edge};
}}
QLabel[role="sidebar-note"] {{ color: {t.faint}; font-size: 12px; }}

/* Text */
QLabel[role="title"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 50px; font-weight: 800; color: {t.text};
}}
QLabel[role="subtitle"] {{ color: {t.muted}; font-size: 14px; }}
QLabel[role="eyebrow"] {{ color: {t.accent}; font-size: 12px; font-weight: 700; }}
QLabel[role="overline"] {{ color: {t.muted}; font-size: 12px; font-weight: 700; }}
QLabel[role="section"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 22px; font-weight: 700; color: {t.text};
}}
QLabel[role="caption"] {{ color: {t.muted}; font-size: 13px; }}
QLabel[role="credit"] {{ color: {t.muted}; font-size: 11px; }}
QLabel[role="strong"] {{ color: {t.text}; font-size: 14px; font-weight: 700; }}
QLabel[role="hero"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 40px; font-weight: 700; color: {t.text};
}}
QLabel[role="stat"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 46px; font-weight: 700; color: {t.text};
}}
QLabel[role="score"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 60px; font-weight: 800; color: {t.text};
}}
QLabel[role="team"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 26px; font-weight: 700; color: {t.text};
}}
QLabel[role="status"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 15px; font-weight: 700; color: {t.accent};
}}

/* Cards: dark glass */
QFrame[role="card"] {{
    background: {glass}; border: 1px solid {edge}; border-radius: {CARD_RADIUS}px;
}}
QFrame[role="favourite"] {{
    background: {glass}; border: 1px solid {t.rgba("accent", 0.55)};
    border-radius: {CARD_RADIUS}px;
}}
QFrame[role="card"] QLabel, QFrame[role="favourite"] QLabel {{ border: none; }}

/* Buttons */
QPushButton {{
    background: {t.rgba("surface_high", 0.9)}; color: {t.text}; border: 1px solid {edge};
    border-radius: {PILL_RADIUS}px; padding: 8px 18px; min-height: 18px; font-weight: 600;
}}
QPushButton:hover {{ background: {t.surface_top}; }}
QPushButton:disabled {{ color: {t.faint}; border-color: transparent; }}
QPushButton[role="primary"] {{
    background: {t.accent}; color: {t.accent_ink}; border: 1px solid {t.accent}; font-weight: 700;
}}
QPushButton[role="primary"]:hover {{
    background: {t.accent_hover}; border-color: {t.accent_hover};
}}
QPushButton[role="primary"]:disabled {{
    background: {t.surface_top}; border-color: {t.surface_top}; color: {t.faint};
}}

/* The matches screen: day chips, arrows, links and filters */
QPushButton[role="chip"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 15px; font-weight: 700; color: {t.text};
    background: {glass}; border: 1px solid {edge}; border-radius: {PILL_RADIUS}px;
    padding: 6px 4px; min-height: 36px;
}}
QPushButton[role="chip"][empty="true"] {{ color: {t.muted}; background: transparent; }}
QPushButton[role="chip"]:hover {{ background: {t.surface_high}; }}
QPushButton[role="chip"]:checked {{
    background: {t.accent}; border-color: {t.accent}; color: {t.accent_ink};
}}
QPushButton[role="chip-arrow"] {{
    font-size: 22px; font-weight: 700; color: {t.muted}; background: transparent; border: none;
    padding: 0 6px; min-height: 36px;
}}
QPushButton[role="chip-arrow"]:hover {{ color: {t.accent}; }}
QPushButton[role="link"] {{
    background: transparent; border: none; color: {t.accent}; padding: 2px 4px; font-weight: 700;
}}
QPushButton[role="link"]:hover {{ color: {t.accent_hover}; }}
QPushButton[role="filter"] {{
    background: transparent; color: {t.muted}; border: 1px solid {t.line};
    border-radius: {PILL_RADIUS}px; padding: 6px 16px; min-height: 16px;
}}
QPushButton[role="filter"]:hover {{ color: {t.text}; }}
QPushButton[role="filter"]:checked {{
    color: {t.night}; background: {t.text}; border-color: {t.text};
}}

/* Inputs */
QComboBox, QDateEdit {{
    background: {t.rgba("surface_high", 0.9)}; color: {t.text}; border: 1px solid {edge};
    border-radius: 14px; padding: 7px 12px; min-height: 20px;
}}
QComboBox:hover, QDateEdit:hover {{ border-color: {t.muted}; }}
QComboBox:focus, QDateEdit:focus {{ border-color: {t.accent}; }}
QComboBox:disabled, QDateEdit:disabled {{ color: {t.faint}; background: {glass}; }}
QComboBox::drop-down, QDateEdit::drop-down {{
    subcontrol-origin: padding; subcontrol-position: center right; width: 24px; border: none;
}}
QComboBox::down-arrow, QDateEdit::down-arrow {{
    image: {_icon("chevron-down.svg")}; width: 12px; height: 12px;
}}
QComboBox QAbstractItemView {{
    background: {t.surface_high}; color: {t.text}; border: 1px solid {t.line};
    selection-background-color: {t.surface_top}; selection-color: {t.accent}; outline: none;
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

/* Tables: rows on the card's glass */
QTableWidget {{
    background: transparent; color: {t.text}; border: none; gridline-color: {t.line};
    selection-background-color: {t.surface_top}; selection-color: {t.text};
}}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: {t.rgba("surface_high", 0.85)}; color: {t.muted}; border: none;
    padding: 9px 8px; font-size: 12px; font-weight: 700;
}}
QHeaderView::section:first {{ border-top-left-radius: 12px; border-bottom-left-radius: 12px; }}
QHeaderView::section:last {{ border-top-right-radius: 12px; border-bottom-right-radius: 12px; }}
QTableCornerButton::section {{ background: transparent; border: none; }}

/* Tabs inside a page: pills */
QTabWidget::pane {{ border: none; top: -1px; background: transparent; }}
QTabWidget > QStackedWidget > QWidget {{ background: transparent; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 16px; font-weight: 700;
    background: transparent; color: {t.muted}; padding: 7px 16px; margin-right: 6px;
    border-radius: 16px;
}}
QTabBar::tab:selected {{ color: {t.accent_ink}; background: {t.accent}; }}
QTabBar::tab:hover:!selected {{ color: {t.text}; background: {t.rgba("surface_high", 0.8)}; }}

QStatusBar {{ background: {t.night}; color: {t.muted}; border-top: 1px solid {edge}; }}
QToolTip {{
    background: {t.surface_top}; color: {t.text}; border: 1px solid {t.line}; padding: 6px;
}}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{
    background: {t.rgba("surface_top", 0.9)}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:hover {{ background: {t.line}; }}
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
