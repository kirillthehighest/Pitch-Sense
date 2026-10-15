"""The change of colours between leagues (Phase 21): the window is already painted in the new
league's palette, and a picture of the old window covers it; a circle opening from the top-left
corner cuts through the picture until it has passed the three other corners.

The cover lets every click through, so the window can be used during the 0.7 seconds.
"""

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

DURATION_MS = 700
EDGE_WIDTH = 3.0  # the glowing line at the edge of the circle


def reveal_radius(progress: float, width: float, height: float) -> float:
    """The circle's radius at ``progress`` (0 to 1): from nothing to the distance between the
    top-left corner and the bottom-right one, the farthest of the other three."""
    return progress * math.hypot(width, height)


class ThemeReveal(QWidget):
    """Covers ``parent`` with ``old`` (a picture of it before the change) and opens a circle in
    it from the top-left corner; removes itself when the circle has passed every corner."""

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

    def _advance(self, value: float) -> None:
        self.progress = float(value)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        area = QRectF(self.rect())
        radius = self.radius
        circle = QPainterPath()
        circle.addEllipse(QPointF(0, 0), radius, radius)
        cover = QPainterPath()
        cover.addRect(area)
        painter.setClipPath(cover.subtracted(circle))
        painter.drawPixmap(self.rect(), self.old)
        painter.setClipping(False)
        if 0 < radius:
            edge = QColor(self.edge)
            edge.setAlphaF(0.9 * (1 - self.progress) + 0.1)
            painter.setPen(QPen(edge, EDGE_WIDTH))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(0, 0), radius, radius)
        painter.end()
