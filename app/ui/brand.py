"""The PitchSense logo, the app icon, the league flags and the team badges, drawn with QPainter.

The logo (Phase 21) is the letters PS in Kanit's black italic, cut by a rising slash: white above
the cut, the league's accent below it, so the mark takes the colours of the league on screen. The
app icon puts it on a tile of the league's night, lit by the league's glow. The team chose it
over earlier monograms that looked too much like a design program's icon; the reasons are in
``docs/brand.md``.

A team's badge is its club crest when ``assets/crests`` has one (Phase 19, collected from
Wikipedia by ``tools/crests.py``; the crests belong to the clubs), otherwise its three letters.
"""

import json
import math
import re
from functools import cache

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.data.paths import ASSETS_DIR
from app.services.labels import team_abbreviation
from app.ui.theme import DISPLAY_FAMILY, LOGO_FAMILY
from app.ui.themes import Theme, current_theme

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)
PIXEL_RATIO = 2  # pixmaps are drawn at twice their size, sharp on high-density screens
CUT_ANGLE = math.radians(15)  # the slash rises to the right
CUT_HEIGHT = 0.56  # where the slash crosses the letters, from their top
CUT_GAP = 0.09  # its width, as a share of the letters' height
TILE_RADIUS = 0.23  # of the icon's side, as macOS draws its icons
CRESTS_DIR = ASSETS_DIR / "crests"  # <crest_slug(team)>.png, at most 128 pixels
LEAGUE_PHOTOS_DIR = ASSETS_DIR / "leagues"  # <code>.jpg, supplied by the team, see sources.json
DEFAULT_TOP = 0.1  # where the banner's strip of an image starts, as a share of its height
# A crest whose pixels are nearly all darker than this luminance vanishes on the dark surfaces
# (Juventus, Tottenham, Derby...), so it is drawn on a light disc.
LIGHT_LUMINANCE = 0.25
LIGHT_SHARE = 0.1
CREST_DISC = "#E9EDF5"

# Round flags of the leagues' countries: (kind, colours); stripes are listed top to bottom or
# left to right, a cross is (background, cross)
FLAGS = {
    "E0": ("cross", ("#FFFFFF", "#CE1124")),
    "SP1": ("spain", ("#AA151B", "#F1BF00")),
    "I1": ("vertical", ("#009246", "#F1F2F1", "#CE2B37")),
    "D1": ("horizontal", ("#000000", "#DD0000", "#FFCE00")),
    "F1": ("vertical", ("#0055A4", "#F1F2F1", "#EF4135")),
}


@cache
def _letters() -> QPainterPath:
    """The outline of PS in Kanit's black italic, overlapping contours merged."""
    font = QFont(LOGO_FAMILY)
    font.setPixelSize(200)
    font.setWeight(QFont.Weight.Black)
    font.setItalic(True)
    path = QPainterPath()
    path.addText(0, 0, font, "PS")
    path.setFillRule(Qt.FillRule.WindingFill)
    return path.simplified()


def _strip(centre: QPointF, offset_from: float, offset_to: float, reach: float) -> QPainterPath:
    """The region between two lines parallel to the slash, at signed distances from ``centre``."""
    along = QPointF(math.cos(CUT_ANGLE), -math.sin(CUT_ANGLE))
    across = QPointF(-along.y(), along.x())  # pointing down
    corners = [(-reach, offset_from), (reach, offset_from), (reach, offset_to), (-reach, offset_to)]
    points = [centre + along * u + across * v for u, v in corners]
    path = QPainterPath()
    path.addPolygon(QPolygonF(points))
    path.closeSubpath()
    return path


def logo_parts(rect: QRectF) -> tuple[QPainterPath, QPainterPath]:
    """The mark fitted and centred in ``rect``: the letters above the slash and below it."""
    letters = _letters()
    bounds = letters.boundingRect()
    scale = min(rect.width() / bounds.width(), rect.height() / bounds.height())
    fitted = QTransform().scale(scale, scale).map(letters)
    bounds = fitted.boundingRect()
    fitted.translate(
        rect.center().x() - bounds.center().x(), rect.center().y() - bounds.center().y()
    )
    bounds = fitted.boundingRect()
    height, reach = bounds.height(), bounds.width() * 2
    centre = QPointF(bounds.center().x(), bounds.top() + height * CUT_HEIGHT)
    half_gap = height * CUT_GAP / 2
    above = fitted.intersected(_strip(centre, -reach, -half_gap, reach))
    below = fitted.intersected(_strip(centre, half_gap, reach, reach))
    return above, below


def paint_logo(painter: QPainter, rect: QRectF, theme: Theme | None = None) -> None:
    """Draw the mark into ``rect``: white above the slash, the league's accent below it."""
    theme = theme or current_theme()
    above, below = logo_parts(rect)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.fillPath(above, QColor("#FFFFFF"))
    painter.fillPath(below, QColor(theme.accent))
    painter.restore()


def tile_path(rect: QRectF) -> QPainterPath:
    path = QPainterPath()
    radius = rect.width() * TILE_RADIUS
    path.addRoundedRect(rect, radius, radius)
    return path


def paint_icon(painter: QPainter, rect: QRectF, theme: Theme | None = None) -> None:
    """The app icon: the mark on a near-black tile, lit from its lower corner by the league's
    deep colour."""
    theme = theme or current_theme()
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    tile = tile_path(rect)
    night = QLinearGradient(rect.topLeft(), rect.bottomRight())
    night.setColorAt(0, QColor(theme.surface_top))
    night.setColorAt(1, QColor(theme.night))
    painter.fillPath(tile, QBrush(night))
    glow = QRadialGradient(rect.bottomRight(), rect.width() * 1.1)
    light = QColor(theme.brand).lighter(150)
    light.setAlpha(210)
    glow.setColorAt(0, light)
    light.setAlpha(0)
    glow.setColorAt(1, light)
    painter.fillPath(tile, QBrush(glow))
    painter.restore()
    margin = rect.width() * 0.16
    paint_logo(painter, rect.adjusted(margin, margin, -margin, -margin), theme)


def icon_image(size: int, theme: Theme | None = None) -> QImage:
    """The app icon at one size, filling the square."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    paint_icon(painter, QRectF(0, 0, size, size), theme)
    painter.end()
    return image


def app_icon(theme: Theme | None = None) -> QIcon:
    """The window and taskbar icon, with an image for every usual size."""
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(QPixmap.fromImage(icon_image(size, theme)))
    return icon


def flag_pixmap(code: str, size: int = 22) -> QPixmap:
    """The round flag of a league's country, with a faint ring so it holds on a dark surface."""
    kind, colours = FLAGS[code]
    pixmap = _blank(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    circle = QPainterPath()
    circle.addEllipse(QRectF(0, 0, size, size))
    painter.setClipPath(circle)
    if kind == "cross":
        background, cross = colours
        painter.fillRect(QRectF(0, 0, size, size), QColor(background))
        bar = size * 0.22
        painter.fillRect(QRectF(0, (size - bar) / 2, size, bar), QColor(cross))
        painter.fillRect(QRectF((size - bar) / 2, 0, bar, size), QColor(cross))
    elif kind == "spain":
        red, yellow = colours
        painter.fillRect(QRectF(0, 0, size, size), QColor(red))
        painter.fillRect(QRectF(0, size / 4, size, size / 2), QColor(yellow))
    else:
        step = size / len(colours)
        for index, colour in enumerate(colours):
            band = (
                QRectF(index * step, 0, step + 0.5, size)
                if kind == "vertical"
                else QRectF(0, index * step, size, step + 0.5)
            )
            painter.fillRect(band, QColor(colour))
    painter.setClipping(False)
    ring = QColor(current_theme().text)
    ring.setAlpha(60)
    painter.setPen(QPen(ring, 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QRectF(0.5, 0.5, size - 1, size - 1))
    painter.end()
    return pixmap


def crest_slug(team: str) -> str:
    """The file name of a team's crest: "Nott'm Forest" -> "nott-m-forest"."""
    return re.sub(r"[^a-z0-9]+", "-", team.lower()).strip("-")


@cache
def crest_image(team: str) -> QImage | None:
    """The club's crest, or None when there is none for the team."""
    path = CRESTS_DIR / f"{crest_slug(team)}.png"
    image = QImage(str(path)) if path.is_file() else QImage()
    return None if image.isNull() else image


@cache
def league_photo(code: str) -> QImage | None:
    """The league's photo for the banner of the screens, or None."""
    path = LEAGUE_PHOTOS_DIR / f"{code}.jpg"
    image = QImage(str(path)) if path.is_file() else QImage()
    return None if image.isNull() else image


@cache
def _photo_sources() -> dict[str, dict]:
    path = LEAGUE_PHOTOS_DIR / "sources.json"
    if not path.is_file():
        return {}
    return {entry["competition"]: entry for entry in json.loads(path.read_text(encoding="utf-8"))}


def photo_credit(code: str) -> str | None:
    """Where the league's image comes from, as the banner shows it."""
    entry = _photo_sources().get(code)
    return f"Imagine: {entry['source']}" if entry else None


def photo_top(code: str) -> float:
    """Where the banner's strip of the league's image starts, as a share of the image's height:
    just above the highest head, so no window width cuts the faces."""
    entry = _photo_sources().get(code)
    return float(entry.get("top", DEFAULT_TOP)) if entry else DEFAULT_TOP


def is_dark(image: QImage) -> bool:
    """True when fewer than ``LIGHT_SHARE`` of the visible pixels are light enough to stand out
    on the dark surfaces."""
    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = rgba.width(), rgba.height()
    rows = np.frombuffer(rgba.constBits(), dtype=np.uint8).reshape(height, rgba.bytesPerLine())
    pixels = rows[:, : width * 4].reshape(height, width, 4).astype(float) / 255
    visible = pixels[..., 3] > 0.5
    if not visible.any():
        return True
    luminance = pixels[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
    return float((luminance[visible] > LIGHT_LUMINANCE).mean()) < LIGHT_SHARE


@cache
def _crest_is_dark(team: str) -> bool:
    crest = crest_image(team)
    return crest is not None and is_dark(crest)


def team_badge(team: str, size: int = 40, highlighted: bool = False) -> QPixmap:
    """The club's crest, or a round badge with the team's three letters; "your team" gets a ring
    in the league's accent. A dark crest sits on a light disc."""
    crest = crest_image(team)
    if crest is not None:
        return _crest_badge(crest, size, highlighted, _crest_is_dark(team))
    pixmap = _blank(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    theme = current_theme()
    ring = max(1.5, size / 20)
    painter.setPen(QPen(QColor(theme.accent if highlighted else theme.line), ring))
    painter.setBrush(QColor(theme.surface_top))
    painter.drawEllipse(QRectF(ring / 2, ring / 2, size - ring, size - ring))
    font = QFont(DISPLAY_FAMILY)
    font.setPixelSize(round(size * (0.36 if size >= 40 else 0.42)))
    font.setWeight(QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(theme.accent if highlighted else theme.text))
    centre = Qt.AlignmentFlag.AlignCenter
    painter.drawText(QRectF(0, 0, size, size), centre, team_abbreviation(team))
    painter.end()
    return pixmap


def _crest_badge(crest: QImage, size: int, highlighted: bool, dark: bool) -> QPixmap:
    pixmap = _blank(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    area = QRectF(0, 0, size, size)
    ring = max(1.5, size / 20)
    if dark:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(CREST_DISC))
        painter.drawEllipse(QRectF(ring / 2, ring / 2, size - ring, size - ring))
    if highlighted:
        painter.setPen(QPen(QColor(current_theme().accent), ring))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(ring / 2, ring / 2, size - ring, size - ring))
    if highlighted or dark:
        area = area.adjusted(size * 0.17, size * 0.17, -size * 0.17, -size * 0.17)
    scale = min(area.width() / crest.width(), area.height() / crest.height())
    width, height = crest.width() * scale, crest.height() * scale
    painter.drawImage(
        QRectF(area.center().x() - width / 2, area.center().y() - height / 2, width, height),
        crest,
    )
    painter.end()
    return pixmap


def paint_pitch(painter: QPainter, rect: QRectF, colour: QColor) -> None:
    """Pitch lines for a background: the halfway line, the centre circle and spot and a penalty
    area, filling the height of ``rect`` from its middle to the right."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(colour, 1.5))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    height = rect.height()
    middle = rect.left() + rect.width() * 0.62
    painter.drawLine(QPointF(middle, rect.top()), QPointF(middle, rect.bottom()))
    centre = QPointF(middle, rect.center().y())
    painter.drawEllipse(centre, height * 0.42, height * 0.42)
    painter.setBrush(colour)
    painter.drawEllipse(centre, 2.5, 2.5)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    box_width, box_height = height * 0.55, height * 1.1
    painter.drawRect(
        QRectF(rect.right() - box_width, centre.y() - box_height / 2, box_width + 2, box_height)
    )
    painter.restore()


def _blank(size: int) -> QPixmap:
    pixmap = QPixmap(size * PIXEL_RATIO, size * PIXEL_RATIO)
    pixmap.setDevicePixelRatio(PIXEL_RATIO)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


class LogoWidget(QWidget):
    """The mark at a fixed size, in the colours of the league on screen."""

    def __init__(self, size: int) -> None:
        super().__init__()
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        paint_logo(painter, QRectF(self.rect()))
        painter.end()


class Lockup(QWidget):
    """The mark beside the wordmark, PITCH in white and SENSE in the league's accent, in Kanit's
    heavy italic; ``compact``, the mark alone (a narrow window)."""

    def __init__(self, height: int = 40) -> None:
        super().__init__()
        self.mark_height = height
        self.word_font = QFont(LOGO_FAMILY)
        self.word_font.setPixelSize(round(height * 0.62))
        self.word_font.setWeight(QFont.Weight.ExtraBold)
        self.word_font.setItalic(True)
        metrics = QFontMetricsF(self.word_font)
        self.mark_width = height * 1.45
        self.text_left = self.mark_width + height * 0.3
        self.full_width = round(self.text_left + metrics.horizontalAdvance("PITCHSENSE") + 4)
        self.compact = False
        self.setFixedSize(self.full_width, height)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setToolTip("PitchSense")

    def set_compact(self, compact: bool) -> None:
        self.compact = compact
        self.setFixedWidth(round(self.mark_width) + 2 if compact else self.full_width)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        theme = current_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_logo(painter, QRectF(0, 0, self.mark_width, self.mark_height), theme)
        if self.compact:
            painter.end()
            return
        painter.setFont(self.word_font)
        metrics = QFontMetricsF(self.word_font)
        baseline = (self.mark_height + metrics.capHeight()) / 2
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QPointF(self.text_left, baseline), "PITCH")
        painter.setPen(QColor(theme.accent))
        painter.drawText(
            QPointF(self.text_left + metrics.horizontalAdvance("PITCH"), baseline), "SENSE"
        )
        painter.end()
