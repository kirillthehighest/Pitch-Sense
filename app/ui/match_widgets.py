"""The pieces of the matches screen (Phase 19): the strip of days, a league's heading and one
match as a row of the list, painted like a scoreboard app's."""

from collections.abc import Collection
from datetime import date, timedelta

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from app.data.models import Outcome
from app.prediction.outputs import ModelName
from app.services.formatting import MONTHS, WEEKDAYS, day_name, percent
from app.services.predictions import MatchForecast
from app.ui.brand import team_badge
from app.ui.theme import DISPLAY_FAMILY, FONT_FAMILY
from app.ui.themes import current_theme
from app.visualization.palette import AWAY, DRAW, HOME, LOSS, NIGHT, WIN

LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
CENTRE = Qt.AlignmentFlag.AlignCenter
OUTCOMES = (Outcome.HOME_WIN, Outcome.DRAW, Outcome.AWAY_WIN)
OUTCOME_COLOURS = {Outcome.HOME_WIN: HOME, Outcome.DRAW: DRAW, Outcome.AWAY_WIN: AWAY}
OUTCOME_INKS = {Outcome.HOME_WIN: "#FFFFFF", Outcome.DRAW: NIGHT, Outcome.AWAY_WIN: "#FFFFFF"}


def chip_text(day: date, today: date) -> str:
    """Two lines for a day chip: "AZI" over "15 OCT.", or "SÂM." over "17 OCT."."""
    name = day_name(day, today)
    first = name if name in ("Azi", "Mâine", "Ieri") else WEEKDAYS[day.weekday()]
    return f"{first}\n{day.day} {MONTHS[day.month - 1]}".upper()


class DayStrip(QWidget):
    """Seven days around the chosen one, as chips, with arrows to move a week; days without
    matches are dimmed but can still be chosen."""

    day_chosen = Signal(object)  # a date
    DAYS = 7

    def __init__(self) -> None:
        super().__init__()
        self.today = date.today()
        self.selected = self.today
        self._match_days: frozenset[date] = frozenset()
        self.earlier_button = QPushButton("‹")
        self.later_button = QPushButton("›")
        for button, step in ((self.earlier_button, -self.DAYS), (self.later_button, self.DAYS)):
            button.setProperty("role", "chip-arrow")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _, s=step: self.choose(self.selected + timedelta(s)))
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.chips: list[QPushButton] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.earlier_button)
        for _ in range(self.DAYS):
            chip = QPushButton()
            chip.setProperty("role", "chip")
            chip.setCheckable(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            chip.clicked.connect(lambda _, c=chip: self.choose(c.property("day")))
            self._group.addButton(chip)
            layout.addWidget(chip, stretch=1)
            self.chips.append(chip)
        layout.addWidget(self.later_button)

    def show_days(self, selected: date, today: date, match_days: Collection[date]) -> None:
        """Centre the strip on ``selected``; ``match_days`` are the days with matches."""
        self.today = today
        self._match_days = frozenset(match_days)
        self.selected = selected
        first = selected - timedelta(days=self.DAYS // 2)
        for offset, chip in enumerate(self.chips):
            day = first + timedelta(days=offset)
            chip.setProperty("day", day)
            chip.setText(chip_text(day, today))
            chip.setChecked(day == selected)
            chip.setProperty("empty", day not in self._match_days)
            chip.style().unpolish(chip)
            chip.style().polish(chip)

    def choose(self, day: date) -> None:
        self.show_days(day, self.today, self._match_days)
        self.day_chosen.emit(day)


class ProbabilityHeading(QWidget):
    """The names of the three probability columns of the match rows, aligned over them."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(20)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        if self.width() < MatchRow.NARROW:
            return  # the rows are stacked: their probabilities are not in columns
        painter = QPainter(self)
        font = QFont(FONT_FAMILY)
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(current_theme().muted))
        width = MatchRow.PROBABILITY_WIDTH
        left = self.width() - 12 - 3 * width - 2 * 6
        for index, name in enumerate(("GAZDE", "EGAL", "OASPEȚI")):
            box = QRectF(left + index * (width + 6), 0, width, self.height())
            painter.drawText(box, CENTRE, name)
        painter.end()


class MatchRow(QAbstractButton):
    """One match of the list: kickoff (or the final whistle), both teams with their crests, and
    either the score or the chosen model's three probabilities, the most likely one filled.

    A played match also says whether that model's most likely outcome happened. ``stacked`` puts
    the teams on one line and the probabilities under them, for narrow columns; a row narrower
    than ``NARROW`` stacks itself. The last row of a list (``last``) draws no line under itself,
    so nothing crosses the card's round corners.
    """

    NARROW = 560
    HEIGHT = 66
    STACKED_HEIGHT = 80
    TIME_WIDTH = 64
    STACKED_TIME_WIDTH = 40
    PROBABILITY_WIDTH = 58
    SCORE_WIDTH = 36

    def __init__(
        self,
        forecast: MatchForecast,
        model: ModelName,
        favourite: str | None = None,
        show_date: bool = False,
        stacked: bool = False,
    ) -> None:
        super().__init__()
        self.forecast = forecast
        self.model = model
        self.favourite = favourite
        self.show_date = show_date
        self.always_stacked = stacked
        self.stacked = stacked
        self.last = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(self.STACKED_HEIGHT if stacked else self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setToolTip("Deschide meciul")

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt's name)
        return QSize(320 if self.stacked else 640, self.height())

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt's name)
        return QSize(280, self.height())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        stacked = self.always_stacked or event.size().width() < self.NARROW
        if stacked != self.stacked:
            self.stacked = stacked
            self.setFixedHeight(self.STACKED_HEIGHT if stacked else self.HEIGHT)
        super().resizeEvent(event)

    @property
    def status_text(self) -> str:
        """What the left column says: the date or kickoff, "Final", or "Amânat"."""
        forecast = self.forecast
        if self.show_date:
            return f"{forecast.match_date:%d.%m}"
        if forecast.played is not None:
            return "Final"
        if forecast.postponed:
            return "Amânat"
        return f"{forecast.kickoff_time:%H:%M}" if forecast.kickoff_time else "–"

    @property
    def hit(self) -> bool | None:
        """Whether the model's most likely outcome happened; None before the match."""
        prediction = self.forecast.of(self.model)
        if self.forecast.played is None or prediction is None:
            return None
        return prediction.probabilities.most_likely == self.forecast.played.result

    def enterEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        theme = current_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        area = QRectF(self.rect())
        if self.underMouse():
            hover = QPainterPath()
            hover.addRoundedRect(area.adjusted(6, 3, -6, -3), 14, 14)
            fill = QColor(theme.surface_high)
            fill.setAlpha(190)
            painter.fillPath(hover, fill)
        if not self.last:
            painter.fillRect(
                QRectF(16, area.height() - 1, area.width() - 32, 1), QColor(255, 255, 255, 16)
            )
        if self.stacked:
            self._paint_stacked(painter, area)
            painter.end()
            return
        self._paint_status(painter, QRectF(12, 0, self.TIME_WIDTH, area.height()))
        right = area.width() - 12
        probabilities_width = 3 * self.PROBABILITY_WIDTH + 2 * 6
        self._paint_probabilities(
            painter, QRectF(right - probabilities_width, 0, probabilities_width, area.height())
        )
        right -= probabilities_width + 18
        if self.forecast.played is not None:
            self._paint_score(painter, QRectF(right - self.SCORE_WIDTH, 7, self.SCORE_WIDTH, 52))
            right -= self.SCORE_WIDTH + 12
        left = 12 + self.TIME_WIDTH + 10
        for line, team in enumerate((self.forecast.home_team, self.forecast.away_team)):
            self._paint_team(painter, QRectF(left, 9 + line * 25, right - left, 22), team)
        painter.end()

    def _paint_stacked(self, painter: QPainter, area: QRectF) -> None:
        """Teams and score on the first line, the probabilities across the second."""
        self._paint_status(painter, QRectF(8, 8, self.STACKED_TIME_WIDTH, 24))
        left = 8 + self.STACKED_TIME_WIDTH + 6
        right = area.width() - 8
        played = self.forecast.played
        if played is not None:
            font = QFont(DISPLAY_FAMILY)
            font.setPixelSize(18)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor(current_theme().text))
            painter.drawText(
                QRectF(right - 50, 8, 50, 24), RIGHT, f"{played.home_goals}–{played.away_goals}"
            )
            right -= 56
        half = (right - left - 14) / 2
        self._paint_team(painter, QRectF(left, 9, half, 22), self.forecast.home_team)
        self._paint_team(painter, QRectF(left + half + 14, 9, half, 22), self.forecast.away_team)
        width = area.width() - 8 - left
        self._paint_probabilities(painter, QRectF(left, 40, width, 34), (width - 12) / 3)

    def _paint_status(self, painter: QPainter, box: QRectF) -> None:
        font = QFont(DISPLAY_FAMILY)
        font.setPixelSize(17)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        theme = current_theme()
        upcoming = self.forecast.played is None and not self.forecast.postponed
        painter.setPen(QColor(theme.text if upcoming and not self.show_date else theme.muted))
        painter.drawText(box, LEFT, self.status_text.upper())

    def _paint_team(self, painter: QPainter, box: QRectF, team: str) -> None:
        favourite = team == self.favourite
        painter.drawPixmap(int(box.left()), int(box.top()), team_badge(team, 22, favourite))
        font = QFont(FONT_FAMILY)
        font.setPixelSize(14)
        played = self.forecast.played
        won = played is not None and (
            (team == played.home_team and played.result is Outcome.HOME_WIN)
            or (team == played.away_team and played.result is Outcome.AWAY_WIN)
        )
        font.setWeight(QFont.Weight.Bold if won else QFont.Weight.DemiBold)
        painter.setFont(font)
        theme = current_theme()
        painter.setPen(QColor(theme.accent if favourite else theme.text))
        text_box = box.adjusted(28, 0, 0, 0)
        name = QFontMetrics(font).elidedText(
            team, Qt.TextElideMode.ElideRight, int(text_box.width())
        )
        painter.drawText(text_box, LEFT, name)

    def _paint_score(self, painter: QPainter, box: QRectF) -> None:
        played = self.forecast.played
        theme = current_theme()
        pill = QPainterPath()
        pill.addRoundedRect(box, 12, 12)
        fill = QColor(theme.surface_top)
        fill.setAlpha(220)
        painter.fillPath(pill, fill)
        font = QFont(DISPLAY_FAMILY)
        font.setPixelSize(19)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(theme.text))
        half = box.height() / 2
        for line, goals in enumerate((played.home_goals, played.away_goals)):
            cell = QRectF(box.left(), box.top() + line * half, box.width(), half)
            painter.drawText(cell, CENTRE, str(goals))

    def _paint_probabilities(
        self, painter: QPainter, box: QRectF, chip_width: float = PROBABILITY_WIDTH
    ) -> None:
        prediction = self.forecast.of(self.model)
        font = QFont(FONT_FAMILY)
        font.setPixelSize(13)
        theme = current_theme()
        if prediction is None:
            painter.setFont(font)
            painter.setPen(QColor(theme.muted))
            painter.drawText(box, RIGHT, "fără predicție")
            return
        probabilities = prediction.probabilities
        best = probabilities.most_likely
        hit = self.hit
        for index, outcome in enumerate(OUTCOMES):
            chip = QRectF(
                box.left() + index * (chip_width + 6), box.center().y() - 15, chip_width, 30
            )
            path = QPainterPath()
            path.addRoundedRect(chip, 15, 15)
            chosen = outcome is best
            if chosen:
                painter.fillPath(path, QColor(OUTCOME_COLOURS[outcome]))
                if hit is not None:  # a played match: a green tick when right, a red cross not
                    painter.setPen(QPen(QColor(WIN if hit else LOSS), 2))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRoundedRect(chip.adjusted(-2, -2, 2, 2), 17, 17)
                    _paint_mark(painter, QPointF(chip.right() - 1, chip.top() + 1), hit)
            else:
                idle = QColor(theme.surface_high)
                idle.setAlpha(170)
                painter.fillPath(path, idle)
            font.setWeight(QFont.Weight.Bold if chosen else QFont.Weight.Medium)
            painter.setFont(font)
            painter.setPen(QColor(OUTCOME_INKS[outcome] if chosen else theme.muted))
            painter.drawText(chip, CENTRE, percent(probabilities.of(outcome), 0))


def _paint_mark(painter: QPainter, centre: QPointF, hit: bool) -> None:
    """A small disc with a tick (the most likely outcome happened) or a cross (it did not): the
    shape says it, the colour only repeats it."""
    radius = 7.0
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(WIN if hit else LOSS))
    painter.drawEllipse(centre, radius, radius)
    pen = QPen(QColor("#FFFFFF"), 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    x, y = centre.x(), centre.y()
    if hit:
        painter.drawPolyline(
            [QPointF(x - 3.2, y), QPointF(x - 0.8, y + 2.6), QPointF(x + 3.4, y - 2.6)]
        )
    else:
        painter.drawLine(QPointF(x - 2.6, y - 2.6), QPointF(x + 2.6, y + 2.6))
        painter.drawLine(QPointF(x - 2.6, y + 2.6), QPointF(x + 2.6, y - 2.6))
    painter.restore()
