"""The PitchSense logo, the app icon, the league flags and the team badges, drawn with QPainter.

The logo is a monogram on a rounded tile, as a scoreboard app has: the letters P and S, heavy and
geometric, white on a tile that runs from Barça blue to garnet, and nothing else. The reasons are
in ``docs/brand.md``.
"""

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from app.services.labels import team_abbreviation
from app.ui.theme import DISPLAY_FAMILY
from app.visualization.palette import (
    BLAU,
    GOLD,
    GRANA,
    LINE,
    SURFACE_TOP,
    TEXT,
)

LOGO_UNITS = 100.0  # the logo is drawn on a 100 x 100 square
TILE_RADIUS = 23.0  # rounded corners, as macOS draws its icons
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)
PIXEL_RATIO = 2  # pixmaps are drawn at twice their size, sharp on high-density screens

# Round flags of the leagues' countries: (kind, colours); stripes are listed top to bottom or
# left to right, a cross is (background, cross)
FLAGS = {
    "E0": ("cross", ("#FFFFFF", "#CE1124")),
    "SP1": ("spain", ("#AA151B", "#F1BF00")),
    "I1": ("vertical", ("#009246", "#F1F2F1", "#CE2B37")),
    "D1": ("horizontal", ("#000000", "#DD0000", "#FFCE00")),
    "F1": ("vertical", ("#0055A4", "#F1F2F1", "#EF4135")),
}


@dataclass(frozen=True, slots=True)
class MonogramGeometry:
    """The measures of the letters, in logo units. Both letters have the same stroke and height;
    the S is two half-rings stacked so that their middle strokes coincide."""

    stroke: float
    top: float
    height: float
    bowl_radius: float  # outer radius of the P's round bowl
    gap: float  # between the P and the S

    @property
    def s_radius(self) -> float:
        return (self.height + self.stroke) / 4

    @property
    def left(self) -> float:
        """Where the P starts, so that the pair is centred on the tile."""
        width = 2 * self.bowl_radius + self.gap + 2 * self.s_radius
        return (LOGO_UNITS - width) / 2

    @property
    def bowl_centre(self) -> tuple[float, float]:
        return self.left + self.bowl_radius, self.top + self.bowl_radius

    @property
    def counter_radius(self) -> float:
        """The round hole of the P."""
        return self.bowl_radius - self.stroke


MONOGRAM = MonogramGeometry(stroke=11.0, top=19.0, height=62.0, bowl_radius=22.5, gap=3.0)


def _circle(x: float, y: float, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(QPointF(x, y), radius, radius)
    return path


def _box(x: float, y: float, width: float, height: float) -> QPainterPath:
    path = QPainterPath()
    path.addRect(QRectF(x, y, width, height))
    return path


def _ring(x: float, y: float, radius: float, stroke: float) -> QPainterPath:
    return _circle(x, y, radius).subtracted(_circle(x, y, radius - stroke))


def letter_p(shape: MonogramGeometry = MONOGRAM) -> QPainterPath:
    """The P: a stem and a round bowl joined to it by straight strokes at its top and bottom."""
    x, y = shape.bowl_centre
    radius, stroke = shape.bowl_radius, shape.stroke
    path = _box(shape.left, shape.top, stroke, shape.height)
    path = path.united(_ring(x, y, radius, stroke))
    path = path.united(_box(shape.left, shape.top, radius, stroke))
    return path.united(_box(shape.left, y + radius - stroke, radius, stroke))


def letter_s(shape: MonogramGeometry = MONOGRAM) -> QPainterPath:
    """The S: an upper half-ring open at its lower right and a lower one open at its upper left,
    sharing their middle stroke."""
    radius, stroke = shape.s_radius, shape.stroke
    x = shape.left + 2 * shape.bowl_radius + shape.gap + radius
    upper_y = shape.top + radius
    lower_y = upper_y + 2 * radius - stroke
    upper = _ring(x, upper_y, radius, stroke).subtracted(_box(x, upper_y, radius + 1, radius + 1))
    lower = _ring(x, lower_y, radius, stroke).subtracted(
        _box(x - radius - 1, lower_y - radius - 1, radius + 1, radius + 1)
    )
    return upper.united(lower)


def tile_path() -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, LOGO_UNITS, LOGO_UNITS), TILE_RADIUS, TILE_RADIUS)
    return path


def paint_logo(painter: QPainter, rect: QRectF) -> None:
    """Draw the logo into the square ``rect``: the tile and the letters."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(rect.topLeft())
    painter.scale(rect.width() / LOGO_UNITS, rect.height() / LOGO_UNITS)
    blaugrana = QLinearGradient(0, 0, LOGO_UNITS, LOGO_UNITS)
    blaugrana.setColorAt(0, QColor(BLAU))
    blaugrana.setColorAt(1, QColor(GRANA))
    painter.fillPath(tile_path(), QBrush(blaugrana))
    painter.fillPath(letter_p(), QColor(TEXT))
    painter.fillPath(letter_s(), QColor(TEXT))
    painter.restore()


def icon_image(size: int) -> QImage:
    """The app icon at one size: the logo tile, filling the square."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    paint_logo(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def app_icon() -> QIcon:
    """The window and taskbar icon, with an image for every usual size."""
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(QPixmap.fromImage(icon_image(size)))
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
    ring = QColor(TEXT)
    ring.setAlpha(60)
    painter.setPen(QPen(ring, 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QRectF(0.5, 0.5, size - 1, size - 1))
    painter.end()
    return pixmap


def team_badge(team: str, size: int = 40, highlighted: bool = False) -> QPixmap:
    """A round badge with the team's three letters; gold-ringed for "your team"."""
    pixmap = _blank(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    ring = max(1.5, size / 20)
    painter.setPen(QPen(QColor(GOLD if highlighted else LINE), ring))
    painter.setBrush(QColor(SURFACE_TOP))
    painter.drawEllipse(QRectF(ring / 2, ring / 2, size - ring, size - ring))
    font = QFont(DISPLAY_FAMILY)
    font.setPixelSize(round(size * (0.36 if size >= 40 else 0.42)))
    font.setWeight(QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(GOLD if highlighted else TEXT))
    centre = Qt.AlignmentFlag.AlignCenter
    painter.drawText(QRectF(0, 0, size, size), centre, team_abbreviation(team))
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
    """The logo tile at a fixed size."""

    def __init__(self, size: int) -> None:
        super().__init__()
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        paint_logo(painter, QRectF(self.rect()))
        painter.end()


class Lockup(QWidget):
    """The logo tile beside the wordmark: PITCH in white, SENSE in gold, condensed and heavy."""

    def __init__(self, height: int = 40) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(round(height * 0.3))
        layout.addWidget(LogoWidget(height))
        self.wordmark = QLabel(
            f'<span style="color:{TEXT}">PITCH</span><span style="color:{GOLD}">SENSE</span>'
        )
        self.wordmark.setStyleSheet(
            f'font-family: "{DISPLAY_FAMILY}"; font-size: {round(height * 0.66)}px; '
            "font-weight: 800; background: transparent;"
        )
        layout.addWidget(self.wordmark)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
