"""The brand: the logo's geometry and colours, the app icon, the flags, the team badges, the
bundled typefaces and the contrast of every text colour on its surfaces."""

import math

import pytest
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QRawFont

from app.data.competitions import COMPETITIONS
from app.ui.brand import (
    CREST_DISC,
    FLAGS,
    ICON_SIZES,
    LOGO_UNITS,
    MONOGRAM,
    Lockup,
    LogoWidget,
    app_icon,
    crest_image,
    crest_slug,
    flag_pixmap,
    icon_image,
    is_dark,
    letter_p,
    letter_s,
    paint_logo,
    team_badge,
)
from app.ui.theme import DISPLAY_FAMILY, FONT_FAMILY, FONTS_DIR, STYLE_SHEET, apply_theme
from app.visualization.palette import (
    AWAY,
    BACKGROUND,
    BLAU,
    DRAW,
    FORM_DRAW,
    GOLD,
    GOLD_TINT,
    GRANA,
    HOME,
    LINE,
    LOSS,
    MUTED,
    NIGHT,
    SURFACE,
    SURFACE_HIGH,
    SURFACE_TOP,
    TEXT,
    WIN,
)

ROMANIAN = "ăâîșțĂÂÎȘȚ"
SCALE = 4  # the logo is drawn at 400 x 400 pixels to read its colours


def colour_at(image: QImage, x: float, y: float) -> str:
    return image.pixelColor(round(x), round(y)).name()


def close_to(colour: QColor, expected: str, tolerance: int = 40) -> bool:
    target = QColor(expected)
    return all(
        abs(a - b) <= tolerance
        for a, b in zip(colour.getRgb()[:3], target.getRgb()[:3], strict=True)
    )


@pytest.fixture(scope="module")
def logo_image(application):
    image = QImage(100 * SCALE, 100 * SCALE, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    paint_logo(painter, QRectF(0, 0, image.width(), image.height()))
    painter.end()
    return image


# --- the logo ---


def test_the_letters_are_side_by_side_centred_and_of_one_height():
    p_box, s_box = letter_p().boundingRect(), letter_s().boundingRect()

    assert not letter_p().intersects(letter_s())
    assert s_box.left() - p_box.right() == pytest.approx(MONOGRAM.gap)
    assert (p_box.top(), p_box.bottom()) == pytest.approx((s_box.top(), s_box.bottom()))
    assert p_box.left() == pytest.approx(LOGO_UNITS - s_box.right())  # centred across
    assert p_box.top() == pytest.approx(MONOGRAM.top)
    assert p_box.height() == pytest.approx(MONOGRAM.height)


def test_the_bowl_of_the_p_is_a_round_hole_that_meets_the_stem():
    x, y = MONOGRAM.bowl_centre
    stem_right = MONOGRAM.left + MONOGRAM.stroke

    assert x - MONOGRAM.counter_radius == pytest.approx(stem_right)
    assert not letter_p().contains(QPointF(x, y))  # the hole is open
    for angle in range(0, 360, 30):  # and the P surrounds it on every side
        edge = MONOGRAM.counter_radius + MONOGRAM.stroke / 2
        point = QPointF(
            x + edge * math.cos(math.radians(angle)), y + edge * math.sin(math.radians(angle))
        )
        assert letter_p().contains(point)


def test_the_logo_is_only_white_letters_on_a_blaugrana_tile(logo_image):
    x, y = MONOGRAM.bowl_centre
    stem = (MONOGRAM.left + MONOGRAM.stroke / 2) * SCALE
    # The gradient runs along the diagonal: the hole of the P shows the tile exactly as the
    # empty margin above the letters does at the same point of the diagonal.
    margin_x = x + y - 5

    assert colour_at(logo_image, stem, 75 * SCALE) == TEXT.lower()
    assert colour_at(logo_image, x * SCALE, y * SCALE) == colour_at(
        logo_image, margin_x * SCALE, 5 * SCALE
    )
    assert close_to(logo_image.pixelColor(8 * SCALE, 12 * SCALE), BLAU)  # top left
    assert close_to(logo_image.pixelColor(92 * SCALE, 88 * SCALE), GRANA)  # bottom right
    assert logo_image.pixelColor(1, 1).alpha() == 0  # rounded corner
    pixels = [
        logo_image.pixelColor(column, row)
        for row in range(0, logo_image.height(), 4)
        for column in range(0, logo_image.width(), 4)
    ]
    assert not any(close_to(colour, GOLD) for colour in pixels if colour.alpha() == 255)


def test_a_logo_widget_is_square(application):
    widget = LogoWidget(40)

    assert (widget.width(), widget.height()) == (40, 40)


def test_the_wordmark_reads_pitchsense(application):
    lockup = Lockup(40)
    wordmark = lockup.wordmark

    assert "PITCH" in wordmark.text() and "SENSE" in wordmark.text()
    assert GOLD in wordmark.text()  # SENSE is gold


# --- the icon ---


@pytest.mark.parametrize("size", [16, 64, 256])
def test_the_icon_is_the_logo_tile(application, size):
    image = icon_image(size)

    assert (image.width(), image.height()) == (size, size)
    assert image.pixelColor(0, 0).alpha() == 0  # rounded corner
    assert image.pixelColor(size // 2, size - 3).alpha() == 255  # the tile reaches the edge


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


def test_your_team_wears_a_gold_ring(application):
    plain = team_badge("Alpha", 40).toImage()  # no crest: the team's letters
    yours = team_badge("Alpha", 40, highlighted=True).toImage()
    ring = (plain.width() // 2, 2)

    assert colour_at(yours, *ring) == GOLD.lower()
    assert colour_at(plain, *ring) == LINE.lower()


def test_a_club_with_a_crest_shows_it(application):
    crest = crest_image("Barcelona")
    assert crest is not None
    assert max(crest.width(), crest.height()) <= 128  # a low resolution
    assert crest_image("Alpha") is None

    plain = team_badge("Barcelona", 40).toImage()
    yours = team_badge("Barcelona", 40, highlighted=True).toImage()
    ring = (plain.width() // 2, 2)

    assert colour_at(yours, *ring) == GOLD.lower()
    assert colour_at(plain, *ring) != LINE.lower()  # no letters badge
    centre = plain.pixelColor(plain.width() // 2, plain.height() // 2)
    assert centre.alpha() > 0  # the crest is drawn


def test_a_dark_crest_sits_on_a_light_disc(application):
    assert is_dark(crest_image("Juventus"))
    assert not is_dark(crest_image("Barcelona"))
    badge = team_badge("Juventus", 40).toImage()

    # Between the disc's edge and the crest, inset by a sixth of the badge
    assert colour_at(badge, badge.width() * 0.1, badge.height() / 2) == CREST_DISC.lower()
    assert badge.pixelColor(0, 0).alpha() == 0  # round


def test_crests_are_named_after_the_teams():
    assert crest_slug("Nott'm Forest") == "nott-m-forest"
    assert crest_slug("Ath Madrid") == "ath-madrid"
    assert crest_slug("Ajaccio GFCO") == "ajaccio-gfco"


# --- typefaces ---


def test_applying_the_theme_again_changes_nothing(application):
    style = application.style().name()

    assert apply_theme(application)  # both typefaces load
    assert application.styleSheet() == STYLE_SHEET
    assert application.style().name() == style


def test_the_bundled_typefaces_are_used_and_write_romanian(application):
    assert QFont().family() == FONT_FAMILY  # set by the theme of the test application
    families = QFontDatabase.families()
    assert FONT_FAMILY in families and DISPLAY_FAMILY in families
    fonts = sorted(FONTS_DIR.glob("*.ttf"))
    assert [path.stem for path in fonts] == [
        "BarlowCondensed-Bold",
        "BarlowCondensed-ExtraBold",
        "BarlowCondensed-Medium",
        "BarlowCondensed-SemiBold",
        "LibreFranklin-Bold",
        "LibreFranklin-ExtraBold",
        "LibreFranklin-Medium",
        "LibreFranklin-Regular",
        "LibreFranklin-SemiBold",
    ]
    for path in fonts:
        glyphs = QRawFont(str(path), 14).glyphIndexesForString(ROMANIAN)
        assert len(glyphs) == len(ROMANIAN) and all(glyphs), path.name
    for licence in ("OFL-BarlowCondensed.txt", "OFL-LibreFranklin.txt"):
        assert (FONTS_DIR / licence).is_file()


# --- contrast ---


def contrast(foreground, background):
    """The WCAG contrast ratio of two colours."""

    def luminance(colour):
        channels = [value / 255 for value in QColor(colour).getRgb()[:3]]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


SURFACES = (NIGHT, BACKGROUND, SURFACE, SURFACE_HIGH, SURFACE_TOP)


@pytest.mark.parametrize(
    ("text", "surface"),
    [(TEXT, surface) for surface in (*SURFACES, GOLD_TINT)]
    + [(MUTED, surface) for surface in SURFACES],  # secondary text is never on a highlighted row
)
def test_text_is_readable_on_every_surface(application, text, surface):
    assert contrast(text, surface) >= 4.5  # WCAG AA for body text


@pytest.mark.parametrize(
    ("text", "background"),
    [(NIGHT, GOLD), (GOLD, BACKGROUND), (GOLD, SURFACE), (NIGHT, DRAW)]
    + [("#FFFFFF", colour) for colour in (HOME, AWAY, WIN, FORM_DRAW, LOSS)],
)
def test_accents_and_painted_labels_are_readable(application, text, background):
    assert contrast(text, background) >= 4.5


def test_gold_buttons_carry_dark_text():
    assert f"background: {GOLD}; color: {NIGHT}" in STYLE_SHEET
