"""Display pieces shared by the screens: cards, labels, tabs, tables, charts and the painted
pieces of the brand (the hero banner, the blaugrana stripe, stat tiles, probability bars, form
squares and the league buttons).

Text and numbers are already Romanian when they reach these widgets (``app/services/formatting.py``
and ``labels.py``); the look comes from the style sheet in ``theme.py`` and the palette.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.services.formatting import percent
from app.services.labels import OUTCOME_LABELS, RESULT_LETTERS
from app.ui.brand import paint_pitch
from app.ui.theme import DISPLAY_FAMILY, FONT_FAMILY
from app.visualization.palette import (
    AWAY,
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
    TEXT,
    WIN,
)

TABLE_ROW_HEIGHT = 36
RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter


def label(text: str = "", role: str | None = None, wrap: bool = False) -> QLabel:
    """A label with a style role from the style sheet (title, section, caption, stat...)."""
    widget = QLabel(text)
    if role:
        widget.setProperty("role", role)
    widget.setWordWrap(wrap)
    return widget


def card(title: str | None = None, role: str = "card") -> tuple[QFrame, QVBoxLayout]:
    """A raised card with an optional section title (in capitals); returns the card and its
    layout."""
    frame = QFrame()
    frame.setProperty("role", role)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(12)
    if title:
        layout.addWidget(label(title.upper(), "section"))
    return frame, layout


def unreadable_log_text(details: str) -> str:
    """The in-place explanation when results cannot be read; the details stay in English, as the
    code that raised them wrote them."""
    return (
        "Rezultatele nu pot fi citite. Rulează din nou backtestul ca să refaci jurnalul "
        f"predicțiilor.\nDetalii: {details}"
    )


class PageTabs(QTabWidget):
    """Tabs that are as tall as the page on show, not as the tallest page: a short page of charts
    beside a long page of tables leaves no empty space under the charts. Tab names are capitals."""

    def __init__(self) -> None:
        super().__init__()
        self.currentChanged.connect(self._fit)

    def addTab(self, page: QWidget, name: str) -> int:  # noqa: N802 (Qt's name)
        return super().addTab(page, name.upper())

    def tabInserted(self, index: int) -> None:  # noqa: N802 (Qt's name)
        super().tabInserted(index)
        self._fit(self.currentIndex())

    def _fit(self, current: int) -> None:
        # A stacked layout leaves pages with an Ignored size policy out of its size.
        for index in range(self.count()):
            policy = (
                QSizePolicy.Policy.Preferred if index == current else QSizePolicy.Policy.Ignored
            )
            self.widget(index).setSizePolicy(policy, policy)
        self.updateGeometry()


def make_table(headers: Sequence[str], stretch_column: int | None = None) -> QTableWidget:
    """A read-only table; ``stretch_column`` (usually a name column) takes the spare width."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(list(headers))
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setShowGrid(False)
    table.setIconSize(QSize(26, 26))
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setStretchLastSection(False)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    if stretch_column is not None:
        header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)
    return table


def fill_table(
    table: QTableWidget,
    rows: Sequence[Sequence[str]],
    fit: bool = False,
    highlight: Collection[int] = (),
    icons: Sequence[QIcon | None] = (),
    icon_column: int = 0,
) -> None:
    """Replace the table's rows; numbers, and the headers of columns of numbers, are right-aligned;
    ``highlight`` rows ("your team") get the gold tint and bold text; ``icons`` (one per row, or
    none) go before the text of ``icon_column``.

    With ``fit`` the table becomes exactly as tall as its rows, for short tables whose rows
    should all be visible without scrolling.
    """
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column, text in enumerate(row):
            item = QTableWidgetItem(text)
            if _looks_numeric(text):
                item.setTextAlignment(RIGHT)
            if row_index in highlight:
                item.setBackground(QBrush(QColor(GOLD_TINT)))
                font = QFont(item.font())
                font.setBold(True)
                item.setFont(font)
            if column == icon_column and row_index < len(icons) and icons[row_index] is not None:
                item.setIcon(icons[row_index])
            table.setItem(row_index, column, item)
    for column in range(table.columnCount()):
        header = table.horizontalHeaderItem(column)
        numbers = bool(rows) and all(_looks_numeric(row[column]) for row in rows)
        if header is not None:
            header.setTextAlignment(RIGHT if numbers else LEFT)
    if fit:
        height = table.horizontalHeader().sizeHint().height() + 2 * table.frameWidth()
        height += table.verticalHeader().defaultSectionSize() * len(rows)
        table.setFixedHeight(height)


class ChartView(QWidget):
    """Shows one matplotlib figure at a time, or a message when there is no chart."""

    def __init__(self, message: str = "") -> None:
        super().__init__()
        self.setMinimumSize(360, 300)
        self.message_label = QLabel(message)
        self.message_label.setProperty("role", "caption")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self.message_label)
        self._canvas: FigureCanvasQTAgg | None = None

    @property
    def figure(self) -> Figure | None:
        """The figure on display, or None while a message is shown."""
        return None if self._canvas is None else self._canvas.figure

    def show_figure(self, figure: Figure) -> None:
        self._remove_canvas()
        self.message_label.hide()
        self._canvas = FigureCanvasQTAgg(figure)
        self._canvas.setStyleSheet(f"background: {SURFACE};")
        self._layout.addWidget(self._canvas)

    def show_message(self, message: str) -> None:
        self._remove_canvas()
        self.message_label.setText(message)
        self.message_label.show()

    def _remove_canvas(self) -> None:
        if self._canvas is not None:
            # Detach at once: a widget only removed from the layout stays painted until deleted.
            self._layout.removeWidget(self._canvas)
            self._canvas.setParent(None)
            self._canvas.deleteLater()
            self._canvas = None


class BrandStripe(QWidget):
    """The thin line under the top bar: blue on the left half, garnet on the right."""

    def __init__(self, height: int = 3) -> None:
        super().__init__()
        self.setFixedHeight(height)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        half = self.width() / 2
        painter.fillRect(QRectF(0, 0, half, self.height()), QColor(BLAU))
        painter.fillRect(QRectF(half, 0, self.width() - half, self.height()), QColor(GRANA))
        painter.end()


class HeroBanner(QWidget):
    """The head of every screen: a night gradient lit blue and garnet, faint pitch lines, the
    league as a gold eyebrow with its flag, the screen's name in large capitals and a subtitle."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(148)
        self.flag_label = QLabel()
        self.eyebrow_label = label(role="eyebrow")
        self.title_label = label(role="title")
        self.subtitle_label = label(role="subtitle", wrap=True)
        eyebrow = QHBoxLayout()
        eyebrow.setSpacing(8)
        eyebrow.addWidget(self.flag_label)
        eyebrow.addWidget(self.eyebrow_label)
        eyebrow.addStretch()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 18)
        layout.setSpacing(2)
        layout.addLayout(eyebrow)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addStretch()

    def show_page(self, title: str, subtitle: str) -> None:
        self.title_label.setText(title.upper())
        self.subtitle_label.setText(subtitle)

    def show_league(self, eyebrow: str, flag: QPixmap | None) -> None:
        self.eyebrow_label.setText(eyebrow.upper())
        if flag is None:
            self.flag_label.clear()
        else:
            self.flag_label.setPixmap(flag)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        area = QRectF(self.rect())
        night = QLinearGradient(0, 0, area.width(), 0)
        night.setColorAt(0, QColor(NIGHT))
        night.setColorAt(1, QColor("#101A3A"))
        painter.fillRect(area, QBrush(night))
        for colour, centre, alpha in (
            (BLAU, QPointF(area.width() * 0.08, 0), 120),
            (GRANA, QPointF(area.width() * 0.95, area.height()), 90),
        ):
            glow = QRadialGradient(centre, area.width() * 0.45)
            tint = QColor(colour)
            tint.setAlpha(alpha)
            glow.setColorAt(0, tint)
            tint.setAlpha(0)
            glow.setColorAt(1, tint)
            painter.fillRect(area, QBrush(glow))
        lines = QColor(TEXT)
        lines.setAlpha(26)
        paint_pitch(painter, area.adjusted(0, -10, 0, 10), lines)
        painter.fillRect(QRectF(0, area.height() - 1, area.width(), 1), QColor(LINE))
        painter.end()


class StatTile(QFrame):
    """A large number with its name in small capitals under it, like a scoreboard."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.setProperty("role", "card")
        self.value_label = label("–", "stat")
        self.name_label = label(name.upper(), "overline")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 14, 22, 16)
        layout.setSpacing(0)
        layout.addWidget(self.value_label)
        layout.addWidget(self.name_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


@dataclass(frozen=True, slots=True)
class BarRow:
    """One model's probabilities, home, draw and away, summing to 1."""

    label: str
    home: float
    draw: float
    away: float


class ProbabilityBars(QWidget):
    """For each model, one bar split into home win, draw and away win, with the percentages
    inside; the most likely outcome is in bold. A legend under the bars names the colours."""

    ROW_HEIGHT = 36
    LABEL_WIDTH = 150
    LEGEND_HEIGHT = 30
    COLOURS = (HOME, DRAW, AWAY)
    INKS = ("#FFFFFF", NIGHT, "#FFFFFF")  # the text on each segment

    def __init__(self) -> None:
        super().__init__()
        self.rows: tuple[BarRow, ...] = ()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._resize()

    def set_rows(self, rows: Sequence[BarRow]) -> None:
        self.rows = tuple(rows)
        self._resize()
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt's name)
        return QSize(460, self._height())

    def _height(self) -> int:
        return len(self.rows) * self.ROW_HEIGHT + (self.LEGEND_HEIGHT if self.rows else 0)

    def _resize(self) -> None:
        self.setFixedHeight(self._height())

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        name_font = QFont(FONT_FAMILY)
        name_font.setPixelSize(13)
        name_font.setWeight(QFont.Weight.DemiBold)
        left = self.LABEL_WIDTH
        width = max(self.width() - left, 60)
        for index, row in enumerate(self.rows):
            top = index * self.ROW_HEIGHT + 6
            painter.setFont(name_font)
            painter.setPen(QColor(TEXT))
            painter.drawText(QRectF(0, top, left - 10, 24), LEFT, row.label)
            self._paint_bar(painter, QRectF(left, top, width, 24), row)
        if self.rows:
            self._paint_legend(painter, len(self.rows) * self.ROW_HEIGHT + 8)
        painter.end()

    def _paint_bar(self, painter: QPainter, area: QRectF, row: BarRow) -> None:
        values = (row.home, row.draw, row.away)
        best = values.index(max(values))
        outline = QPainterPath()
        outline.addRoundedRect(area, 6, 6)
        painter.save()
        painter.setClipPath(outline)
        x = area.left()
        for index, value in enumerate(values):
            segment = area.width() * value
            last = index == len(values) - 1
            width = area.right() - x if last else max(segment - 2, 0)  # a 2-pixel gap
            box = QRectF(x, area.top(), width, area.height())
            painter.fillRect(box, QColor(self.COLOURS[index]))
            text = percent(value)
            font = QFont(FONT_FAMILY)
            font.setPixelSize(12)
            font.setWeight(QFont.Weight.Bold if index == best else QFont.Weight.Medium)
            if QFontMetrics(font).horizontalAdvance(text) + 10 <= width:
                painter.setFont(font)
                painter.setPen(QColor(self.INKS[index]))
                painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
            x += segment
        painter.restore()

    def _paint_legend(self, painter: QPainter, top: float) -> None:
        font = QFont(FONT_FAMILY)
        font.setPixelSize(12)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        x = float(self.LABEL_WIDTH)
        for colour, code in zip(self.COLOURS, ("H", "D", "A"), strict=True):
            painter.fillRect(QRectF(x, top + 4, 10, 10), QColor(colour))
            painter.setPen(QColor(MUTED))
            name = OUTCOME_LABELS[code]
            painter.drawText(QPointF(x + 16, top + 13), name)
            x += 16 + metrics.horizontalAdvance(name) + 22


class FormStrip(QWidget):
    """The last results as coloured squares with V, E or Î, oldest first, like a form guide."""

    SQUARE = 24
    GAP = 6
    COLOURS = {"W": WIN, "D": FORM_DRAW, "L": LOSS}

    def __init__(self) -> None:
        super().__init__()
        self.results: tuple[str, ...] = ()
        self.setFixedHeight(self.SQUARE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_results(self, results: Sequence[str]) -> None:
        """``results`` are W, D or L codes, oldest first."""
        unknown = set(results) - set(self.COLOURS)
        if unknown:
            raise ValueError(f"unknown result codes: {sorted(unknown)}")
        self.results = tuple(results)
        self.setFixedWidth(max(len(self.results) * (self.SQUARE + self.GAP) - self.GAP, 1))
        self.update()

    @property
    def letters(self) -> str:
        return " ".join(RESULT_LETTERS[result] for result in self.results)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont(DISPLAY_FAMILY)
        font.setPixelSize(15)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        for index, result in enumerate(self.results):
            box = QRectF(index * (self.SQUARE + self.GAP), 0, self.SQUARE, self.SQUARE)
            path = QPainterPath()
            path.addRoundedRect(box, 6, 6)
            painter.fillPath(path, QColor(self.COLOURS[result]))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, RESULT_LETTERS[result])
        painter.end()


class LeagueButton(QAbstractButton):
    """A league in the side panel: its round flag, its name and its country; the chosen league is
    raised and marked with gold on its left edge."""

    def __init__(self, code: str, name: str, country: str, flag: QPixmap) -> None:
        super().__init__()
        self.code = code
        self.setText(name)
        self.country = country
        self._flag = flag
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(54)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt's name)
        return QSize(220, 54)

    def enterEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        area = QRectF(self.rect()).adjusted(8, 3, -8, -3)
        if self.isChecked() or self.underMouse():
            path = QPainterPath()
            path.addRoundedRect(area, 10, 10)
            painter.fillPath(path, QColor(SURFACE_HIGH if self.isChecked() else SURFACE))
        if self.isChecked():
            marker = QRectF(area.left(), area.top() + 10, 3, area.height() - 20)
            painter.fillRect(marker, QColor(GOLD))
        flag_size = self._flag.width() / self._flag.devicePixelRatio()
        painter.drawPixmap(QPointF(area.left() + 14, area.center().y() - flag_size / 2), self._flag)
        text_left = area.left() + 14 + flag_size + 12
        name_font = QFont(FONT_FAMILY)
        name_font.setPixelSize(14)
        name_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(name_font)
        painter.setPen(QColor(TEXT if self.isChecked() or self.underMouse() else "#D5DAE6"))
        painter.drawText(QRectF(text_left, area.top() + 7, area.width(), 20), LEFT, self.text())
        country_font = QFont(FONT_FAMILY)
        country_font.setPixelSize(12)
        painter.setFont(country_font)
        painter.setPen(QColor(MUTED))
        painter.drawText(QRectF(text_left, area.top() + 26, area.width(), 18), LEFT, self.country)
        painter.end()


def _looks_numeric(text: str) -> bool:
    """True for Romanian numbers such as 12, 2.486, −0,0073, +0,0056 or 53,4%, and for the dash
    of a number that is not available; False for 2010/11 or 2–1."""
    if text == "–":
        return True
    plain = text.replace("%", "").replace("−", "-").replace(".", "").replace(",", ".").strip()
    try:
        float(plain)
    except ValueError:
        return False
    return True
