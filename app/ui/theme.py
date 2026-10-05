"""The look of the interface: two typefaces, the dark brand palette and one style sheet.

The application uses Qt's Fusion style everywhere, so macOS and Windows look the same, and its own
dark palette, whatever the system's colour scheme. Widgets are styled through object names and
the ``role`` property, never one by one, so the whole look lives in ``STYLE_SHEET``. Libre
Franklin sets the text; Barlow Condensed, a condensed sports face, sets titles, numbers and the
navigation, always in capitals.
"""

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

from app.data.paths import ASSETS_DIR
from app.visualization.palette import (
    BACKGROUND,
    FAINT,
    GOLD,
    GOLD_HOVER,
    LINE,
    MUTED,
    NIGHT,
    SURFACE,
    SURFACE_HIGH,
    SURFACE_TOP,
    TEXT,
)

FONT_FAMILY = "Libre Franklin"
DISPLAY_FAMILY = "Barlow Condensed"
FONTS_DIR = ASSETS_DIR / "fonts"  # static weights, SIL Open Font License (OFL-*.txt)
ICONS_DIR = ASSETS_DIR / "icons"  # the drop-down chevron and the tick of a checkbox
BODY_PIXELS = 14


def _icon(name: str) -> str:
    """A style-sheet reference to a bundled icon (the path may hold spaces and accents)."""
    return f'url("{(ICONS_DIR / name).as_posix()}")'


STYLE_SHEET = f"""
QWidget {{ color: {TEXT}; font-family: "{FONT_FAMILY}"; font-size: {BODY_PIXELS}px; }}
QMainWindow, QWidget#page, QStackedWidget#pages, QScrollArea,
QScrollArea > QWidget > QWidget, QDialog {{
    background: {BACKGROUND};
}}
QLabel {{ background: transparent; }}

/* Top bar and side panel */
QFrame#topbar {{ background: {NIGHT}; border: none; }}
QPushButton[role="nav"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 18px; font-weight: 600; color: {MUTED};
    background: transparent; border: none; border-bottom: 3px solid transparent;
    border-radius: 0; padding: 20px 14px 17px 14px;
}}
QPushButton[role="nav"]:hover {{ color: {TEXT}; }}
QPushButton[role="nav"]:checked {{ color: {TEXT}; border-bottom: 3px solid {GOLD}; }}
QPushButton[role="favourite"] {{
    background: transparent; color: {GOLD}; border: 1px solid {GOLD}; border-radius: 16px;
    padding: 7px 18px; min-height: 18px; font-weight: 700;
}}
QPushButton[role="favourite"]:hover {{ background: {GOLD}; color: {NIGHT}; }}
QFrame#sidepanel {{ background: {NIGHT}; border: none; border-right: 1px solid {LINE}; }}
QLabel[role="sidebar-note"] {{ color: {FAINT}; font-size: 12px; }}

/* Text */
QLabel[role="title"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 46px; font-weight: 800; color: {TEXT};
}}
QLabel[role="subtitle"] {{ color: {MUTED}; font-size: 14px; }}
QLabel[role="eyebrow"] {{ color: {GOLD}; font-size: 12px; font-weight: 700; }}
QLabel[role="overline"] {{ color: {MUTED}; font-size: 12px; font-weight: 700; }}
QLabel[role="section"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 21px; font-weight: 700; color: {TEXT};
}}
QLabel[role="caption"] {{ color: {MUTED}; font-size: 13px; }}
QLabel[role="strong"] {{ color: {TEXT}; font-size: 14px; font-weight: 700; }}
QLabel[role="hero"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 40px; font-weight: 700; color: {TEXT};
}}
QLabel[role="stat"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 46px; font-weight: 700; color: {TEXT};
}}
QLabel[role="score"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 58px; font-weight: 800; color: {TEXT};
}}
QLabel[role="team"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 26px; font-weight: 700; color: {TEXT};
}}
QLabel[role="status"] {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 15px; font-weight: 600; color: {GOLD};
}}

/* Cards */
QFrame[role="card"] {{ background: {SURFACE}; border: 1px solid #1E2640; border-radius: 14px; }}
QFrame[role="favourite"] {{
    background: {SURFACE}; border: 1px solid rgba(237, 187, 0, 0.55); border-radius: 14px;
}}
QFrame[role="card"] QLabel, QFrame[role="favourite"] QLabel {{ border: none; }}

/* Buttons */
QPushButton {{
    background: {SURFACE_HIGH}; color: {TEXT}; border: 1px solid {LINE}; border-radius: 16px;
    padding: 7px 18px; min-height: 18px; font-weight: 600;
}}
QPushButton:hover {{ background: {SURFACE_TOP}; }}
QPushButton:disabled {{ color: {FAINT}; border-color: {SURFACE_HIGH}; }}
QPushButton[role="primary"] {{
    background: {GOLD}; color: {NIGHT}; border: 1px solid {GOLD}; font-weight: 700;
}}
QPushButton[role="primary"]:hover {{ background: {GOLD_HOVER}; border-color: {GOLD_HOVER}; }}
QPushButton[role="primary"]:disabled {{
    background: {SURFACE_TOP}; border-color: {SURFACE_TOP}; color: {FAINT};
}}

/* Inputs */
QComboBox, QDateEdit {{
    background: {SURFACE_HIGH}; color: {TEXT}; border: 1px solid {LINE}; border-radius: 10px;
    padding: 7px 10px; min-height: 20px;
}}
QComboBox:hover, QDateEdit:hover {{ border-color: {MUTED}; }}
QComboBox:focus, QDateEdit:focus {{ border-color: {GOLD}; }}
QComboBox:disabled, QDateEdit:disabled {{ color: {FAINT}; background: {SURFACE}; }}
QComboBox::drop-down, QDateEdit::drop-down {{
    subcontrol-origin: padding; subcontrol-position: center right; width: 22px; border: none;
}}
QComboBox::down-arrow, QDateEdit::down-arrow {{
    image: {_icon("chevron-down.svg")}; width: 12px; height: 12px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE_HIGH}; color: {TEXT}; border: 1px solid {LINE};
    selection-background-color: {SURFACE_TOP}; selection-color: {GOLD}; outline: none;
}}
QCalendarWidget QWidget {{ background: {SURFACE_HIGH}; color: {TEXT}; }}
QCalendarWidget QToolButton {{ background: transparent; color: {TEXT}; border: none; }}
QCalendarWidget QAbstractItemView:enabled {{
    background: {SURFACE}; color: {TEXT}; selection-background-color: {GOLD};
    selection-color: {NIGHT};
}}
QCalendarWidget QAbstractItemView:disabled {{ color: {FAINT}; }}
QRadioButton, QCheckBox {{ spacing: 8px; background: transparent; }}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 14px; height: 14px; border: 2px solid {MUTED}; background: {SURFACE_HIGH};
}}
QRadioButton::indicator {{ border-radius: 9px; }}
QRadioButton::indicator:checked {{
    border-color: {GOLD};
    background: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.5, fx: 0.5, fy: 0.5,
        stop: 0 {GOLD}, stop: 0.55 {GOLD}, stop: 0.6 {SURFACE_HIGH}, stop: 1 {SURFACE_HIGH});
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QCheckBox::indicator:checked {{
    border-color: {GOLD}; background: {GOLD}; image: {_icon("check.svg")};
}}

/* Tables */
QTableWidget {{
    background: {SURFACE}; color: {TEXT}; border: 1px solid {LINE}; border-radius: 12px;
    gridline-color: {LINE}; selection-background-color: {SURFACE_TOP}; selection-color: {TEXT};
}}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: {SURFACE_HIGH}; color: {MUTED}; border: none; border-bottom: 1px solid {LINE};
    padding: 8px 8px; font-size: 12px; font-weight: 700;
}}
QTableCornerButton::section {{ background: {SURFACE_HIGH}; border: none; }}

/* Tabs inside a page */
QTabWidget::pane {{ border: none; top: -1px; background: transparent; }}
QTabWidget > QStackedWidget > QWidget {{ background: transparent; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    font-family: "{DISPLAY_FAMILY}"; font-size: 17px; font-weight: 600;
    background: transparent; color: {MUTED}; padding: 8px 14px; margin-right: 6px;
    border-bottom: 3px solid transparent;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 3px solid {GOLD}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

QStatusBar {{ background: {NIGHT}; color: {MUTED}; border-top: 1px solid {LINE}; }}
QToolTip {{ background: {SURFACE_TOP}; color: {TEXT}; border: 1px solid {LINE}; padding: 6px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: {SURFACE_TOP}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:hover {{ background: {LINE}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


def load_fonts() -> set[str]:
    """Register the bundled typefaces; returns the families that loaded."""
    families: set[str] = set()
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            families.update(QFontDatabase.applicationFontFamilies(font_id))
    return families


def apply_theme(application: QApplication) -> bool:
    """Give the whole application the PitchSense look; False when a bundled typeface did not load
    and a system font stands in for it."""
    application.setStyle("Fusion")
    families = load_fonts()
    font = QFont(FONT_FAMILY if FONT_FAMILY in families else QFont().family())
    font.setPixelSize(BODY_PIXELS)
    application.setFont(font)
    palette = QPalette()
    for role, colour in (
        (QPalette.ColorRole.Window, BACKGROUND),
        (QPalette.ColorRole.Base, SURFACE),
        (QPalette.ColorRole.AlternateBase, SURFACE_HIGH),
        (QPalette.ColorRole.Text, TEXT),
        (QPalette.ColorRole.WindowText, TEXT),
        (QPalette.ColorRole.ButtonText, TEXT),
        (QPalette.ColorRole.Button, SURFACE_HIGH),
        (QPalette.ColorRole.BrightText, GOLD),
        (QPalette.ColorRole.Highlight, GOLD),
        (QPalette.ColorRole.HighlightedText, NIGHT),
        (QPalette.ColorRole.PlaceholderText, FAINT),
        (QPalette.ColorRole.ToolTipBase, SURFACE_TOP),
        (QPalette.ColorRole.ToolTipText, TEXT),
        (QPalette.ColorRole.Light, SURFACE_TOP),
        (QPalette.ColorRole.Midlight, SURFACE_HIGH),
        (QPalette.ColorRole.Mid, LINE),
        (QPalette.ColorRole.Dark, NIGHT),
        (QPalette.ColorRole.Link, GOLD),
    ):
        palette.setColor(role, QColor(colour))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(FAINT))
    application.setPalette(palette)
    application.setStyleSheet(STYLE_SHEET)
    return {FONT_FAMILY, DISPLAY_FAMILY} <= families
