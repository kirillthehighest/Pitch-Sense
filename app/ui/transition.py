"""The change of colours between leagues (Phase 21): the window is already painted in the new
league's palette, and a picture of the old window covers it; a circle opening from the top-left
corner cuts through the picture until it has passed the three other corners.

As in the colour changes of Android's Material You ("Monet"), the circle's edge is not a clean
line but waves running along it, followed by fainter ripples in the new league's accent; the
waves calm down as the circle grows.

The cover lets every click through, so the window can be used during the 0.8 seconds; it paints
only two pictures of the window, so the animation runs at the screen's frame rate.
"""

import math

import numpy as np
from PySide6.QtCore import QEasingCurve, QPointF, QRect, Qt, QVariantAnimation, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRegion,
)
from PySide6.QtWidgets import QWidget

DURATION_MS = 800
WAVELENGTH = 120.0  # pixels along the edge between two crests of the main wave
AMPLITUDE = 18.0  # the waves' height when the circle starts, in pixels...
CALM_AMPLITUDE = 4.0  # ...and when it has passed every corner
STEP = 8.0  # pixels along the edge between two points of its outline
RIPPLES = ((20.0, 0.4), (44.0, 0.2))  # (distance behind the edge, opacity)
GLOW_WIDTH = 9.0  # the soft light along the edge
BAND_ROW = 16  # the height of the strips a frame repaints around the moving edge


def reveal_radius(progress: float, width: float, height: float) -> float:
    """The circle's mean radius at ``progress`` (0 to 1): from nothing to past the bottom-right
    corner, the farthest of the other three, by more than the waves' height."""
    return progress * (math.hypot(width, height) + 2 * AMPLITUDE)


def wave_amplitude(progress: float) -> float:
    """The waves' height: high while the circle is small, calm when it covers the window."""
    return CALM_AMPLITUDE + (AMPLITUDE - CALM_AMPLITUDE) * (1 - progress) ** 0.6


def wave_offset(arc: float, progress: float, amplitude: float) -> float:
    """How far the edge stands out of the circle ``arc`` pixels along it: two waves of different
    lengths, running in opposite directions as ``progress`` grows, so the edge seems to ripple."""
    phase = progress * 4 * math.pi
    main = math.sin(2 * math.pi * arc / WAVELENGTH + phase)
    small = math.sin(2 * math.pi * arc / (WAVELENGTH * 0.57) - 1.6 * phase)
    return amplitude * (0.65 * main + 0.35 * small)


def wave_edge(radius: float, progress: float, amplitude: float | None = None) -> list[QPointF]:
    """The wavy edge of the circle around the top-left corner, from the top edge of the window
    (angle 0) to its left edge (angle 90°), as points."""
    xs, ys = _edge_arrays(
        radius, progress, wave_amplitude(progress) if amplitude is None else amplitude
    )
    return [QPointF(x, y) for x, y in zip(xs.tolist(), ys.tolist(), strict=True)]


def _edge_arrays(radius: float, progress: float, amplitude: float) -> tuple[np.ndarray, np.ndarray]:
    """``wave_edge`` as two arrays of coordinates, computed at once (a frame needs it fast)."""
    if radius <= 0:
        return np.zeros(1), np.zeros(1)
    count = max(24, min(600, math.ceil(radius * math.pi / 2 / STEP)))
    angles = np.linspace(0.0, math.pi / 2, count + 1)
    arc = radius * angles
    phase = progress * 4 * math.pi
    offset = amplitude * (
        0.65 * np.sin(2 * math.pi * arc / WAVELENGTH + phase)
        + 0.35 * np.sin(2 * math.pi * arc / (WAVELENGTH * 0.57) - 1.6 * phase)
    )  # wave_offset, for every point at once
    reach = np.maximum(0.0, radius + offset)
    return reach * np.cos(angles), reach * np.sin(angles)


def band(inner: float, outer: float, width: int, height: int) -> QRegion:
    """The part of a ``width`` × ``height`` window between two circles around its top-left
    corner, as strips: all a frame has to repaint when the edge moves from one to the other."""
    region = QRegion()
    inner, outer = max(0.0, inner), max(0.0, outer)
    for top in range(0, min(height, math.ceil(outer)), BAND_ROW):
        bottom = top + BAND_ROW
        left = math.sqrt(max(inner * inner - bottom * bottom, 0.0))
        right = math.sqrt(max(outer * outer - top * top, 0.0))
        left, right = max(0, math.floor(left)), min(width, math.ceil(right))
        if right > left:
            region += QRect(left, top, right - left, BAND_ROW)
    return region


class ThemeReveal(QWidget):
    """Shows ``old`` (a picture of ``parent`` before the change) and opens a wavy circle in it
    from the top-left corner onto ``new`` (a picture after it); removes itself when the circle
    has passed every corner.

    The cover is opaque and paints only the two pictures, so nothing under it is repainted while
    it runs: each frame costs two image copies and the wavy line, a few milliseconds, whatever
    the window holds. That keeps the animation at the screen's frame rate.
    """

    ended = Signal()

    def __init__(self, parent: QWidget, old: QPixmap, new: QPixmap, edge: str) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.old = old
        self.new = new
        self.edge = QColor(edge)
        self.progress = 0.0
        self._painted_radius = 0.0  # the radius of the frame last painted
        self._old_brush = _picture_brush(old)
        self.setGeometry(parent.rect())
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setDuration(DURATION_MS)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._advance)
        self.animation.finished.connect(self.finish)

    def start(self) -> None:
        self.show()
        self.raise_()
        self.animation.start()

    def finish(self) -> None:
        """End at once (the animation's end, or a new change of league)."""
        self.animation.stop()
        self.hide()
        self.ended.emit()
        self.deleteLater()

    @property
    def radius(self) -> float:
        return reveal_radius(self.progress, self.width(), self.height())

    def cover(self, edge: list[QPointF] | None = None) -> QPainterPath:
        """The part of the window still showing the old picture: outside the wavy circle."""
        width, height = float(self.width()), float(self.height())
        if edge is None:
            edge = wave_edge(self.radius, self.progress)
        start, end = edge[0], edge[-1]  # on the top edge and on the left edge
        outline = [
            QPointF(start.x(), 0),
            QPointF(max(width, start.x()), 0),
            QPointF(max(width, start.x()), max(height, end.y())),
            QPointF(0, max(height, end.y())),
            QPointF(0, end.y()),
            *reversed(edge),
        ]
        path = QPainterPath()
        path.addPolygon(QPolygonF(outline))
        path.closeSubpath()
        return path

    def _advance(self, value: float) -> None:
        """Move the edge, repainting only the strips it crosses, with its glow and ripples."""
        before = self.radius
        self.progress = float(value)
        reach = AMPLITUDE + GLOW_WIDTH
        inner = min(before, self._painted_radius) - reach - RIPPLES[-1][0]
        self.update(band(inner, self.radius + reach, self.width(), self.height()))

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        # Qt limits the painting to the strips ``_advance`` asked for
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.new)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        radius = self.radius
        amplitude = wave_amplitude(self.progress)
        edge = wave_edge(radius, self.progress, amplitude)
        painter.fillPath(self.cover(edge), self._old_brush)  # no clip mask: one pass
        if radius > 0:
            self._paint_ripples(painter, radius, QPolygonF(edge), amplitude)
        self._painted_radius = radius
        painter.end()

    def _paint_ripples(
        self, painter: QPainter, radius: float, edge: QPolygonF, amplitude: float
    ) -> None:
        """A soft glow and a bright line along the edge, and fainter waves behind it."""
        fade = 1 - self.progress * 0.7
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for width, alpha in ((GLOW_WIDTH, 0.14), (2.5, 0.95)):
            colour = QColor(self.edge)
            colour.setAlphaF(alpha * fade)
            pen = QPen(colour, width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawPolyline(edge)
        for distance, alpha in RIPPLES:
            if radius <= distance:
                continue
            colour = QColor(self.edge)
            colour.setAlphaF(alpha * fade)
            painter.setPen(QPen(colour, 1.4))
            ripple = wave_edge(radius - distance, self.progress + distance / 300, amplitude * 0.7)
            painter.drawPolyline(QPolygonF(ripple))


def _picture_brush(picture: QPixmap) -> QBrush:
    """A brush that paints ``picture`` at its place in the window (Qt draws a brush's picture at
    its own pixel density, so a high-density picture keeps its sharpness and its size)."""
    return QBrush(picture)
