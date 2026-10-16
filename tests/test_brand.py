"""The brand: the logo cut by its slash and its colours, the app icon, the flags, the team
badges and the bundled typefaces. The contrast of every league's palette is checked in
``test_themes.py``."""

import pytest
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QImage,
    QPainter,
    QRawFont,
)

from app.data.competitions import COMPETITIONS
from app.services.images import DEFAULT_TOP, crest_slug, photo_credit, photo_top
from app.ui.brand import (
    CREST_DISC,
    CUT_HEIGHT,
    FLAGS,
    ICON_SIZES,
    Lockup,
    LogoWidget,
    app_icon,
    crest_image,
    flag_pixmap,
    icon_image,
    is_dark,
    league_photo,
    logo_parts,
    paint_logo,
    team_badge,
)
from app.ui.theme import (
    DISPLAY_FAMILY,
    FONT_FAMILY,
    FONTS_DIR,
    LOGO_FAMILY,
    STYLE_SHEET,
    apply_theme,
)
from app.ui.themes import THEMES, current_theme

ROMANIAN = "ăâîșțĂÂÎȘȚ"
LOGO_RECT = QRectF(0, 0, 400, 280)


def colour_at(image: QImage, x: float, y: float) -> str:
    return image.pixelColor(round(x), round(y)).name()


def close_to(colour: QColor, expected: str, tolerance: int = 40) -> bool:
    target = QColor(expected)
    return all(
        abs(a - b) <= tolerance
        for a, b in zip(colour.getRgb()[:3], target.getRgb()[:3], strict=True)
    )


def logo_image(theme) -> QImage:
    image = QImage(400, 280, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    paint_logo(painter, LOGO_RECT, theme)
    painter.end()
    return image


def opaque_pixels(image: QImage, step: int = 2) -> list[tuple[int, int, QColor]]:
    return [
        (column, row, colour)
        for row in range(0, image.height(), step)
        for column in range(0, image.width(), step)
        if (colour := image.pixelColor(column, row)).alpha() == 255
    ]


# --- the logo ---


def test_the_slash_cuts_the_letters_in_two(application):
    above, below = logo_parts(LOGO_RECT)
    letters = above.united(below).boundingRect()

    assert not above.isEmpty() and not below.isEmpty()
    assert not above.intersects(below)  # the slash leaves a gap between them
    assert above.boundingRect().top() == pytest.approx(letters.top(), abs=0.5)
    assert below.boundingRect().bottom() == pytest.approx(letters.bottom(), abs=0.5)
    # Across the middle of the letters, where the slash crosses them, nothing is drawn
    cut = letters.top() + letters.height() * CUT_HEIGHT
    centre = QPointF(letters.center().x(), cut)
    assert not above.contains(centre) and not below.contains(centre)


def test_the_slash_rises_to_the_right(application):
    above, _ = logo_parts(LOGO_RECT)
    letters = above.boundingRect()

    def lowest_point(x: float) -> float:  # the lowest y of the part above the slash at x
        ys = [y / 4 for y in range(0, 1120) if above.contains(QPointF(x, y / 4))]
        return max(ys) if ys else float("nan")

    left = lowest_point(letters.left() + letters.width() * 0.2)
    right = lowest_point(letters.left() + letters.width() * 0.8)
    assert right < left  # the cut is higher on the right


def test_the_mark_fits_its_rectangle_and_is_centred(application):
    above, below = logo_parts(LOGO_RECT)
    letters = above.united(below).boundingRect()

    assert LOGO_RECT.adjusted(-0.5, -0.5, 0.5, 0.5).contains(letters)
    assert letters.center().x() == pytest.approx(LOGO_RECT.center().x(), abs=1)
    assert max(letters.width() / LOGO_RECT.width(), letters.height() / LOGO_RECT.height()) > 0.95


@pytest.mark.parametrize("code", sorted(THEMES))
def test_the_mark_is_white_above_the_slash_and_the_league_accent_below(application, code):
    theme = THEMES[code]
    pixels = opaque_pixels(logo_image(theme))
    white = [y for _, y, colour in pixels if close_to(colour, "#FFFFFF", 6)]
    accent = [y for _, y, colour in pixels if close_to(colour, theme.accent, 6)]

    assert white and accent
    assert len(white) + len(accent) == len(pixels)  # only the two colours, no tile
    assert sum(white) / len(white) < sum(accent) / len(accent)
    assert logo_image(theme).pixelColor(1, 1).alpha() == 0  # transparent around the letters


def test_a_logo_widget_is_square(application):
    widget = LogoWidget(40)

    assert (widget.width(), widget.height()) == (40, 40)


def test_the_wordmark_writes_sense_in_the_league_accent(application):
    lockup = Lockup(40)
    image = lockup.grab().toImage()
    accent = current_theme().accent
    sense = lockup.text_left + QFontMetricsF(lockup.word_font).horizontalAdvance("PITCH")
    lean = lockup.word_font.pixelSize() * 0.3  # italic letters lean over their neighbours
    pixels = opaque_pixels(image, 1)
    pitch = [colour for x, _, colour in pixels if lockup.text_left < x < sense - lean]
    words = [colour for x, _, colour in pixels if x > sense + lean]

    assert any(close_to(colour, "#FFFFFF", 6) for colour in pitch)
    assert not any(close_to(colour, accent, 6) for colour in pitch)
    assert any(close_to(colour, accent, 6) for colour in words)
    assert not any(close_to(colour, "#FFFFFF", 6) for colour in words)
    assert lockup.width() == lockup.full_width


def test_a_compact_lockup_keeps_only_the_mark(application):
    lockup = Lockup(40)
    lockup.set_compact(True)

    assert lockup.width() < lockup.text_left
    lockup.set_compact(False)
    assert lockup.width() == lockup.full_width


# --- the icon ---


@pytest.mark.parametrize("size", [16, 64, 256])
def test_the_icon_is_the_mark_on_a_rounded_tile(application, size):
    image = icon_image(size)

    assert (image.width(), image.height()) == (size, size)
    assert image.pixelColor(0, 0).alpha() == 0  # rounded corner
    assert image.pixelColor(size // 2, size - 3).alpha() == 255  # the tile reaches the edge


def test_the_icon_takes_the_league_colours(application):
    premier, serie_a = icon_image(64, THEMES["E0"]), icon_image(64, THEMES["I1"])

    assert premier != serie_a
    pixels = opaque_pixels(icon_image(256, THEMES["E0"]))
    assert any(close_to(colour, THEMES["E0"].accent, 10) for _, _, colour in pixels)


def test_the_app_icon_has_every_size(application):
    assert {size.width() for size in app_icon().availableSizes()} == set(ICON_SIZES)


# --- flags and badges ---


def test_every_league_has_a_flag():
    assert set(FLAGS) == set(COMPETITIONS)


@pytest.mark.parametrize(
    ("code", "points"),
    [
        ("SP1", [((0.5, 0.12), "#aa151b"), ((0.5, 0.5), "#f1bf00")]),
        ("I1", [((0.15, 0.5), "#009246"), ((0.85, 0.5), "#ce2b37")]),
        ("D1", [((0.5, 0.15), "#000000"), ((0.5, 0.85), "#ffce00")]),
        ("F1", [((0.15, 0.5), "#0055a4"), ((0.85, 0.5), "#ef4135")]),
        ("E0", [((0.5, 0.5), "#ce1124"), ((0.25, 0.25), "#ffffff")]),
    ],
)
def test_flags_have_their_countries_colours(application, code, points):
    image = flag_pixmap(code, 40).toImage()

    for (x, y), expected in points:
        assert colour_at(image, x * image.width(), y * image.height()) == expected
    assert image.pixelColor(0, 0).alpha() == 0  # round


def test_your_team_wears_a_ring_in_the_league_accent(application):
    plain = team_badge("Alpha", 40).toImage()  # no crest: the team's letters
    yours = team_badge("Alpha", 40, highlighted=True).toImage()
    ring = (plain.width() // 2, 2)

    assert colour_at(yours, *ring) == current_theme().accent.lower()
    assert colour_at(plain, *ring) == current_theme().line.lower()


def test_a_club_with_a_crest_shows_it(application):
    crest = crest_image("Barcelona")
    assert crest is not None
    assert max(crest.width(), crest.height()) <= 128  # a low resolution
    assert crest_image("Alpha") is None

    plain = team_badge("Barcelona", 40).toImage()
    yours = team_badge("Barcelona", 40, highlighted=True).toImage()
    ring = (plain.width() // 2, 2)

    assert colour_at(yours, *ring) == current_theme().accent.lower()
    assert colour_at(plain, *ring) != current_theme().line.lower()  # no letters badge
    centre = plain.pixelColor(plain.width() // 2, plain.height() // 2)
    assert centre.alpha() > 0  # the crest is drawn


def test_a_dark_crest_sits_on_a_light_disc(application):
    assert is_dark(crest_image("Juventus"))
    assert not is_dark(crest_image("Barcelona"))
    badge = team_badge("Juventus", 40).toImage()

    # Between the disc's edge and the crest, inset by a sixth of the badge
    assert colour_at(badge, badge.width() * 0.1, badge.height() / 2) == CREST_DISC.lower()
    assert badge.pixelColor(0, 0).alpha() == 0  # round


def test_every_league_has_its_image_its_source_and_where_to_cut_it(application):
    for code in COMPETITIONS:
        assert league_photo(code) is not None
        assert photo_credit(code) == "Imagine: DAZN"
        assert 0 <= photo_top(code) < 0.5  # above the faces
    assert photo_credit("XX") is None
    assert photo_top("XX") == DEFAULT_TOP


def test_crests_are_named_after_the_teams():
    assert crest_slug("Nott'm Forest") == "nott-m-forest"
    assert crest_slug("Ath Madrid") == "ath-madrid"
    assert crest_slug("Ajaccio GFCO") == "ajaccio-gfco"


# --- typefaces ---


def test_applying_the_theme_again_changes_nothing(application):
    style = application.style().name()

    assert apply_theme(application)  # every typeface loads
    assert application.styleSheet() == STYLE_SHEET
    assert application.style().name() == style


def test_the_bundled_typefaces_are_used_and_write_romanian(application):
    assert QFont().family() == FONT_FAMILY  # set by the theme of the test application
    families = QFontDatabase.families()
    assert {FONT_FAMILY, DISPLAY_FAMILY, LOGO_FAMILY} <= set(families)
    fonts = sorted(FONTS_DIR.glob("*.ttf"))
    assert [path.stem for path in fonts] == [
        "BarlowCondensed-Bold",
        "BarlowCondensed-ExtraBold",
        "BarlowCondensed-Medium",
        "BarlowCondensed-SemiBold",
        "Kanit-BlackItalic",
        "Kanit-ExtraBoldItalic",
        "PlusJakartaSans-Bold",
        "PlusJakartaSans-ExtraBold",
        "PlusJakartaSans-Medium",
        "PlusJakartaSans-Regular",
        "PlusJakartaSans-SemiBold",
    ]
    for path in fonts:
        glyphs = QRawFont(str(path), 14).glyphIndexesForString(ROMANIAN)
        assert len(glyphs) == len(ROMANIAN) and all(glyphs), path.name
    for licence in ("OFL-BarlowCondensed.txt", "OFL-Kanit.txt", "OFL-PlusJakartaSans.txt"):
        assert (FONTS_DIR / licence).is_file()
