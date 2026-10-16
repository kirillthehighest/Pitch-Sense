"""The pieces of the matches screen (Phase 19, redrawn in Phase 21): the strip of days, the
headings of the probability columns and one match as a row of the list, painted like the score
apps the team chose as references."""

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
from app.visualization.palette import LOSS, WIN

LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
CENTRE = Qt.AlignmentFlag.AlignCenter
OUTCOMES = (Outcome.HOME_WIN, Outcome.DRAW, Outcome.AWAY_WIN)


def chip_text(day: date, today: date) -> str:
    """Two lines for a day chip: "Azi" over "15 oct.", or "Sâm." over "17 oct."."""
    name = day_name(day, today)
    first = name if name in ("Azi", "Mâine", "Ieri") else WEEKDAYS[day.weekday()].capitalize()
    return f"{first}\n{day.day} {MONTHS[day.month - 1]}"


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
    """The names of the three probability columns of the match rows under it, aligned over
    them."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(18)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        if self.width() < MatchRow.NARROW:
            return  # the rows are stacked: their probabilities are not in columns
        painter = QPainter(self)
        font = QFont(FONT_FAMILY)
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(current_theme().muted))
        for index, name in enumerate(("Gazde", "Egal", "Oaspeți")):
            box = MatchRow.chip_box(self.width(), self.height(), index)
            painter.drawText(QRectF(box.left(), 0, box.width(), self.height()), CENTRE, name)
        painter.end()


class MatchRow(QAbstractButton):
    """One match of the list, as in the score apps the team chose: the kickoff (or the final
    whistle), the home team on the left and the away team on the right of the score (or "vs"),
    and the chosen model's three probabilities, the most likely one filled with the accent.

    A played match also says whether that model's most likely outcome happened. ``stacked`` puts
    the teams on one line and the probabilities under them, for narrow columns; a row narrower
    than ``NARROW`` stacks itself. The last row of a list (``last``) draws no line under itself,
    so nothing crosses the card's round corners.
    """

    NARROW = 600
    HEIGHT = 60
    STACKED_HEIGHT = 104
    PADDING = 14
    TIME_WIDTH = 58
    STACKED_TIME_WIDTH = 44
    PROBABILITY_WIDTH = 54
    CHIP_HEIGHT = 30
    CHIP_GAP = 6
    SCORE_WIDTH = 58
    CREST = 24

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
        return QSize(320 if self.stacked else 700, self.height())

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt's name)
        return QSize(280, self.height())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        stacked = self.always_stacked or event.size().width() < self.NARROW
        if stacked != self.stacked:
            self.stacked = stacked
            self.setFixedHeight(self.STACKED_HEIGHT if stacked else self.HEIGHT)
        super().resizeEvent(event)

    @classmethod
    def chip_box(cls, width: float, height: float, index: int) -> QRectF:
        """Where the probability chip ``index`` (home, draw, away) sits in a row of one line."""
        chips = 3 * cls.PROBABILITY_WIDTH + 2 * cls.CHIP_GAP
        left = width - cls.PADDING - chips + index * (cls.PROBABILITY_WIDTH + cls.CHIP_GAP)
        return QRectF(left, (height - cls.CHIP_HEIGHT) / 2, cls.PROBABILITY_WIDTH, cls.CHIP_HEIGHT)

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
            hover.addRoundedRect(area.adjusted(4, 3, -4, -3), 12, 12)
            painter.fillPath(hover, QColor(theme.surface_high))
        if not self.last:
            painter.fillRect(
                QRectF(self.PADDING, area.height() - 1, area.width() - 2 * self.PADDING, 1),
                QColor(255, 255, 255, 14),
            )
        if self.stacked:
            self._paint_stacked(painter, area)
        else:
            self._paint_line(painter, area)
        painter.end()

    def _paint_line(self, painter: QPainter, area: QRectF) -> None:
        """Kickoff, home team, score, away team and the three chips, on one line."""
        self._paint_status(painter, QRectF(self.PADDING, 0, self.TIME_WIDTH, area.height()))
        chips_left = self.chip_box(area.width(), area.height(), 0).left()
        self._paint_probabilities(painter, area.height() / 2, chips_left)
        left = self.PADDING + self.TIME_WIDTH + 6
        right = chips_left - 24
        self._paint_teams(painter, QRectF(left, 0, right - left, area.height()))

    def _paint_stacked(self, painter: QPainter, area: QRectF) -> None:
        """The home team over the away team with the score beside them, the probabilities
        across the line under them: nothing is cut in a narrow column."""
        self._paint_status(painter, QRectF(10, 8, self.STACKED_TIME_WIDTH, 22))
        left = 10 + self.STACKED_TIME_WIDTH + 4
        score = QRectF(area.width() - 10 - 40, 8, 40, 48)
        for line, team in enumerate((self.forecast.home_team, self.forecast.away_team)):
            box = QRectF(left, 8 + line * 26, score.left() - 8 - left, 22)
            self._paint_team(painter, box, team, self.CREST - 4, home_side=True)
        self._paint_stacked_score(painter, score)
        width = (area.width() - 20 - 2 * self.CHIP_GAP) / 3
        self._paint_probabilities(painter, 80, 10, width)

    def _paint_stacked_score(self, painter: QPainter, box: QRectF) -> None:
        """The two scores one over the other in a dark pill, or "vs" before the match."""
        theme = current_theme()
        played = self.forecast.played
        if played is None:
            self._paint_score(painter, QRectF(box.left(), box.center().y() - 13, box.width(), 26))
            return
        pill = QPainterPath()
        pill.addRoundedRect(box, 10, 10)
        painter.fillPath(pill, QColor(theme.surface_high))
        font = QFont(DISPLAY_FAMILY)
        font.setPixelSize(18)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(theme.text))
        half = box.height() / 2
        for line, goals in enumerate((played.home_goals, played.away_goals)):
            cell = QRectF(box.left(), box.top() + line * half, box.width(), half)
            painter.drawText(cell, CENTRE, str(goals))

    def _paint_status(self, painter: QPainter, box: QRectF) -> None:
        font = QFont(FONT_FAMILY)
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        theme = current_theme()
        upcoming = self.forecast.played is None and not self.forecast.postponed
        painter.setPen(
            QColor(theme.accent_text if upcoming and not self.show_date else theme.muted)
        )
        painter.drawText(box, LEFT, self.status_text)

    def _paint_teams(self, painter: QPainter, box: QRectF, small: bool = False) -> None:
        """The home team left of the score, the away team right of it, crests outside."""
        score = self.SCORE_WIDTH - (10 if small else 0)
        centre = box.center().x()
        chip = QRectF(centre - score / 2, box.center().y() - 14, score, 28)
        self._paint_score(painter, chip)
        crest = self.CREST - (4 if small else 0)
        home = QRectF(box.left(), box.top(), chip.left() - 10 - box.left(), box.height())
        away = QRectF(chip.right() + 10, box.top(), box.right() - chip.right() - 10, box.height())
        self._paint_team(painter, home, self.forecast.home_team, crest, home_side=True)
        self._paint_team(painter, away, self.forecast.away_team, crest, home_side=False)

    def _paint_team(
        self, painter: QPainter, box: QRectF, team: str, crest: int, home_side: bool
    ) -> None:
        favourite = team == self.favourite
        badge = team_badge(team, crest, favourite)
        top = round(box.center().y() - crest / 2)
        if home_side:
            painter.drawPixmap(round(box.left()), top, badge)
            text_box = box.adjusted(crest + 10, 0, 0, 0)
        else:
            painter.drawPixmap(round(box.right() - crest), top, badge)
            text_box = box.adjusted(0, 0, -(crest + 10), 0)
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
        painter.setPen(QColor(theme.accent_text if favourite else theme.text))
        name = QFontMetrics(font).elidedText(
            team, Qt.TextElideMode.ElideRight, int(max(text_box.width(), 0))
        )
        painter.drawText(text_box, LEFT if home_side else RIGHT, name)

    def _paint_score(self, painter: QPainter, box: QRectF) -> None:
        """The score in a dark pill, or "vs" before the match."""
        theme = current_theme()
        pill = QPainterPath()
        pill.addRoundedRect(box, 10, 10)
        painter.fillPath(pill, QColor(theme.surface_high))
        played = self.forecast.played
        if played is None:
            font = QFont(FONT_FAMILY)
            font.setPixelSize(12)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.setPen(QColor(theme.muted))
            painter.drawText(box, CENTRE, "vs")
            return
        font = QFont(DISPLAY_FAMILY)
        font.setPixelSize(19)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(theme.text))
        painter.drawText(box, CENTRE, f"{played.home_goals} : {played.away_goals}")

    def _paint_probabilities(
        self,
        painter: QPainter,
        middle: float,
        left: float,
        chip_width: float = PROBABILITY_WIDTH,
    ) -> None:
        prediction = self.forecast.of(self.model)
        font = QFont(FONT_FAMILY)
        font.setPixelSize(13)
        theme = current_theme()
        if prediction is None:
            painter.setFont(font)
            painter.setPen(QColor(theme.muted))
            width = 3 * chip_width + 2 * self.CHIP_GAP
            painter.drawText(QRectF(left, middle - 15, width, 30), RIGHT, "fără predicție")
            return
        probabilities = prediction.probabilities
        best = probabilities.most_likely
        hit = self.hit
        for index, outcome in enumerate(OUTCOMES):
            chip = QRectF(
                left + index * (chip_width + self.CHIP_GAP),
                middle - self.CHIP_HEIGHT / 2,
                chip_width,
                self.CHIP_HEIGHT,
            )
            path = QPainterPath()
            path.addRoundedRect(chip, 10, 10)
            chosen = outcome is best
            painter.fillPath(path, QColor(theme.accent if chosen else theme.surface_high))
            font.setWeight(QFont.Weight.Bold if chosen else QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.setPen(QColor(theme.accent_ink if chosen else theme.muted))
            painter.drawText(chip, CENTRE, percent(probabilities.of(outcome), 0))
            if chosen and hit is not None:  # a played match: a green tick when right, a red cross
                _paint_mark(painter, QPointF(chip.right() - 1, chip.top() + 1), hit)


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
