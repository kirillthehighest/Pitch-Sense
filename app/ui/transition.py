"""The change of colours between leagues (Phase 21): the window is already painted in the new
league's palette, and a picture of the old window covers it; a circle opening from the top-left
corner cuts through the picture until it has passed the three other corners.

As in the colour changes of Android's Material You ("Monet"), the circle's edge is not a clean
line but waves running along it, followed by fainter ripples in the new league's accent; the
waves calm down as the circle grows.

The cover lets every click through, so the window can be used during the 0.8 seconds.
"""

import math

from PySide6.QtCore import QEasingCurve, QPointF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QWidget

DURATION_MS = 800
WAVELENGTH = 120.0  # pixels along the edge between two crests of the main wave
AMPLITUDE = 18.0  # the waves' height when the circle starts, in pixels...
CALM_AMPLITUDE = 4.0  # ...and when it has passed every corner
STEP = 6.0  # pixels along the edge between two points of its outline
RIPPLES = ((22.0, 0.45), (46.0, 0.25), (74.0, 0.12))  # (distance behind the edge, opacity)


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
    if amplitude is None:
        amplitude = wave_amplitude(progress)
    if radius <= 0:
        return [QPointF(0, 0)]
    count = max(24, min(800, math.ceil(radius * math.pi / 2 / STEP)))
    points = []
    for index in range(count + 1):
        angle = math.pi / 2 * index / count
        arc = radius * angle
        reach = max(0.0, radius + wave_offset(arc, progress, amplitude))
        points.append(QPointF(reach * math.cos(angle), reach * math.sin(angle)))
    return points


class ThemeReveal(QWidget):
    """Covers ``parent`` with ``old`` (a picture of it before the change) and opens a wavy circle
    in it from the top-left corner; removes itself when the circle has passed every corner."""

    ended = Signal()

    def __init__(self, parent: QWidget, old: QPixmap, edge: str) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.old = old
        self.edge = QColor(edge)
        self.progress = 0.0
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

    def cover(self) -> QPainterPath:
        """The part of the window still showing the old picture: outside the wavy circle."""
        width, height = float(self.width()), float(self.height())
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
        self.progress = float(value)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipPath(self.cover())
        painter.drawPixmap(self.rect(), self.old)
        painter.setClipping(False)
        radius = self.radius
        if radius > 0:
            self._paint_ripples(painter, radius)
        painter.end()

    def _paint_ripples(self, painter: QPainter, radius: float) -> None:
        """A soft glow and a bright line along the edge, and fainter waves behind it."""
        fade = 1 - self.progress * 0.7
        amplitude = wave_amplitude(self.progress)
        edge = QPolygonF(wave_edge(radius, self.progress, amplitude))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for width, alpha in ((16.0, 0.16), (3.0, 0.95)):
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
            painter.setPen(QPen(colour, 1.6))
            ripple = wave_edge(radius - distance, self.progress + distance / 300, amplitude * 0.7)
            painter.drawPolyline(QPolygonF(ripple))
