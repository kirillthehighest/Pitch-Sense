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
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QBoxLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.services.formatting import percent
from app.services.labels import OUTCOME_LABELS, RESULT_LETTERS
from app.ui.theme import CARD_RADIUS, FONT_FAMILY
from app.ui.themes import Theme, blend, current_theme
from app.visualization.charts import on_surface
from app.visualization.palette import (
    FORM_DRAW,
    GOLD,
    LOSS,
    NIGHT,
    SURFACE,
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
    """A card with an optional section title; returns the card and its layout."""
    frame = QFrame()
    frame.setProperty("role", role)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(24, 22, 24, 22)
    layout.setSpacing(14)
    if title:
        layout.addWidget(label(title, "section"))
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
        return super().addTab(page, name)

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
                item.setBackground(QBrush(QColor(current_theme().accent_tint)))
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
    """Shows one matplotlib figure at a time, or a message when there is no chart. The figure is
    transparent, so it sits on the card's glass in any league's colours."""

    def __init__(self, message: str = "") -> None:
        super().__init__()
        self.setMinimumSize(320, 300)
        self.message_label = QLabel(message)
        self.message_label.setProperty("role", "caption")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self.message_label)
        self._canvas: FigureCanvasQTAgg | None = None
        self._surface = SURFACE  # the colour the figure's rings and gaps were drawn in
        self._highlight = GOLD  # and the colour of its chosen season or team
        self._stale = False  # recoloured while out of sight, not redrawn yet

    @property
    def figure(self) -> Figure | None:
        """The figure on display, or None while a message is shown."""
        return None if self._canvas is None else self._canvas.figure

    def show_figure(self, figure: Figure) -> None:
        self._remove_canvas()
        self._stale = False
        self.message_label.hide()
        self._surface = SURFACE
        self._highlight = GOLD
        self._recolour(figure)
        self._canvas = FigureCanvasQTAgg(figure)
        self._canvas.setStyleSheet("background: transparent;")
        self._layout.addWidget(self._canvas)

    def show_message(self, message: str) -> None:
        self._remove_canvas()
        self.message_label.setText(message)
        self.message_label.show()

    def restyle(self) -> None:
        """Repaint the figure on display in the colours of the league now on screen; a chart
        out of sight is redrawn when it is shown, so a change of league stays quick."""
        if self._canvas is None:
            return
        self._recolour(self._canvas.figure)
        if self.isVisible():
            self._canvas.draw_idle()
        else:
            self._stale = True

    def showEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        if self._stale and self._canvas is not None:
            self._stale = False
            self._canvas.draw_idle()
        super().showEvent(event)

    def _recolour(self, figure: Figure) -> None:
        theme = current_theme()
        on_surface(figure, theme.surface, self._surface, theme.accent, self._highlight)
        self._surface, self._highlight = theme.surface, theme.accent

    def _remove_canvas(self) -> None:
        if self._canvas is not None:
            # Detach at once: a widget only removed from the layout stays painted until deleted.
            self._layout.removeWidget(self._canvas)
            self._canvas.setParent(None)
            self._canvas.deleteLater()
            self._canvas = None


class Backdrop(QWidget):
    """The window's background: the night shared by every league, flat, as in the references."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("backdrop")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(current_theme().background))
        painter.end()


class ResponsiveBox(QWidget):
    """Lays its widgets side by side, or one under the other when it is narrower than
    ``breakpoint``, so no screen needs a horizontal scroll bar."""

    def __init__(self, breakpoint: int, spacing: int = 16) -> None:
        super().__init__()
        self.breakpoint = breakpoint
        self._layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(spacing)
        # Side by side, the layout would make the box at least as wide as all its widgets
        # together, and it could never become narrow enough to stack them.
        self._layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self._stretches: list[int] = []
        self._widths: list[int | None] = []

    @property
    def stacked(self) -> bool:
        return self._layout.direction() == QBoxLayout.Direction.TopToBottom

    def add(
        self, widget: QWidget, stretch: int = 1, top: bool = False, width: int | None = None
    ) -> None:
        """Add a widget with its share of the width side by side (``stretch``); ``top`` keeps it
        at the top of the row instead of stretching it; ``width`` fixes its width side by side
        (one under the other, every widget takes the whole width)."""
        self._stretches.append(stretch)
        self._widths.append(width)
        if width is not None:
            widget.setFixedWidth(width)
        if top:
            self._layout.addWidget(widget, stretch, Qt.AlignmentFlag.AlignTop)
        else:
            self._layout.addWidget(widget, stretch)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        self._arrange(event.size().width())
        super().resizeEvent(event)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt's name)
        """Never wider than the widest widget: below the breakpoint the widgets stack."""
        hint = super().minimumSizeHint()
        widest = max(
            (
                item.widget().minimumSizeHint().width()
                for index in range(self._layout.count())
                if (item := self._layout.itemAt(index)).widget() is not None
            ),
            default=0,
        )
        return QSize(widest, hint.height())

    def _arrange(self, width: int) -> None:
        stacked = width < self.breakpoint
        if stacked == self.stacked:
            return
        self._layout.setDirection(
            QBoxLayout.Direction.TopToBottom if stacked else QBoxLayout.Direction.LeftToRight
        )
        for index, (stretch, fixed) in enumerate(zip(self._stretches, self._widths, strict=True)):
            self._layout.setStretch(index, 0 if stacked else stretch)
            widget = self._layout.itemAt(index).widget()
            if fixed is not None:
                if stacked:
                    widget.setMinimumWidth(0)
                    widget.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX
                else:
                    widget.setFixedWidth(fixed)


def paint_head_card(
    painter: QPainter, area: QRectF, radius: float = CARD_RADIUS, theme: Theme | None = None
) -> None:
    """A card lit from its top by a league's deep colour (``theme``'s, else the league on
    screen's), fading into the card colour: the heads of a match and of a team."""
    theme = theme or current_theme()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    area = area.adjusted(0.5, 0.5, -0.5, -0.5)
    path = QPainterPath()
    path.addRoundedRect(area, radius, radius)
    painter.fillPath(path, QColor(theme.surface))
    light = QLinearGradient(area.topLeft(), area.bottomLeft())
    top, bottom = QColor(theme.brand), QColor(theme.brand)
    top.setAlpha(235)
    bottom.setAlpha(0)
    light.setColorAt(0, top)
    light.setColorAt(0.85, bottom)
    painter.fillPath(path, QBrush(light))
    painter.setPen(QPen(QColor(255, 255, 255, 16), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


class ReflowGrid(QWidget):
    """Widgets in equal columns, as many as fit with at least ``column_width`` each; the rest go
    on the next rows (five league cards: one row in a wide window, 3 + 2 in a narrow one)."""

    def __init__(self, column_width: int, spacing: int = 14) -> None:
        super().__init__()
        self.column_width = column_width
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(spacing)
        self._grid.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.widgets: list[QWidget] = []
        self.columns = 0

    def add(self, widget: QWidget) -> None:
        self.widgets.append(widget)
        self.columns = 0
        self._arrange(self.width())

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt's name)
        return QSize(self.column_width, super().minimumSizeHint().height())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        self._arrange(event.size().width())
        super().resizeEvent(event)

    def _arrange(self, width: int) -> None:
        spacing = self._grid.horizontalSpacing()
        fit = (width + spacing) // (self.column_width + spacing)
        columns = max(1, min(len(self.widgets), fit))
        if columns == self.columns:
            return
        self.columns = columns
        for widget in self.widgets:
            self._grid.removeWidget(widget)
        for index, widget in enumerate(self.widgets):
            self._grid.addWidget(widget, index // columns, index % columns)
        for column in range(len(self.widgets)):
            self._grid.setColumnStretch(column, 1 if column < columns else 0)


class HeroBanner(QWidget):
    """The head of every screen, a rounded card: the league's image on the right at full
    resolution, its left edge running into a fill of the image's own edge colour, so the image
    seems to continue under the title; the league with its flag, the screen's name in large
    capitals, a subtitle, and the image's source in the corner."""

    HEIGHT = 224
    RADIUS = 24
    PHOTO_SHARE = 0.62  # the image takes the right part of the card...
    PHOTO_MAX_WIDTH = 860  # ...but no wider, or a wide window would cut the players' heads
    FADE = 0.5  # the share of the image, from its left edge, that runs into the fill

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(self.HEIGHT)
        self.photo: QImage | None = None
        self.top = 0.1
        self.fill = QColor(current_theme().brand)
        self.flag_label = QLabel()
        self.eyebrow_label = label(role="hero-eyebrow")
        self.title_label = label(role="title")
        self.subtitle_label = label(role="subtitle", wrap=True)
        self.subtitle_label.setMaximumWidth(560)
        self.credit_label = label(role="credit")
        eyebrow = QHBoxLayout()
        eyebrow.setSpacing(8)
        eyebrow.addWidget(self.flag_label)
        eyebrow.addWidget(self.eyebrow_label)
        eyebrow.addStretch()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 22, 12)
        layout.setSpacing(4)
        layout.addLayout(eyebrow)
        layout.addSpacing(2)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addStretch()
        layout.addWidget(self.credit_label, alignment=Qt.AlignmentFlag.AlignRight)

    def show_page(self, title: str, subtitle: str) -> None:
        self.title_label.setText(title.upper())
        self.subtitle_label.setText(subtitle)

    def photo_width(self, width: float) -> float:
        """The width the image takes in a card ``width`` wide."""
        return min(width * self.PHOTO_SHARE, self.PHOTO_MAX_WIDTH) if self.photo else 0.0

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        """Keep the subtitle left of the image, so no text crosses the players."""
        width = event.size().width()
        self.subtitle_label.setMaximumWidth(
            int(max(260, min(560, width - self.photo_width(width) - 48)))
        )
        super().resizeEvent(event)

    def show_league(
        self,
        eyebrow: str,
        flag: QPixmap | None,
        photo: QImage | None = None,
        credit: str | None = None,
        top: float = 0.1,
    ) -> None:
        """``top`` is where the image's strip starts, as a share of its height."""
        self.eyebrow_label.setText(eyebrow)
        if flag is None:
            self.flag_label.clear()
        else:
            self.flag_label.setPixmap(flag)
        self.photo = photo
        self.top = top
        brand = current_theme().brand
        self.fill = (
            QColor(brand) if photo is None else QColor(blend(edge_colour(photo, top), brand, 0.5))
        )
        self.credit_label.setText(credit or "")
        self.resize(self.size())  # the subtitle's room depends on the image
        self.subtitle_label.setMaximumWidth(
            int(max(260, min(560, self.width() - self.photo_width(self.width()) - 48)))
        )
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        area = QRectF(self.rect())
        card = QPainterPath()
        card.addRoundedRect(area, self.RADIUS, self.RADIUS)
        painter.setClipPath(card)
        painter.fillRect(area, self.fill)
        if self.photo is not None:
            # Drawn straight onto the widget, at the screen's own resolution: never through a
            # smaller intermediate image, which would blur it on a high-density screen.
            width = round(self.photo_width(area.width()))
            box = QRectF(area.right() - width, area.top(), width, area.height())
            painter.drawImage(box, self.photo, _cover(self.photo, box, self.top))
            fade = QLinearGradient(box.left(), 0, box.left() + box.width() * self.FADE, 0)
            solid, clear = QColor(self.fill), QColor(self.fill)
            clear.setAlpha(0)
            fade.setColorAt(0, solid)
            fade.setColorAt(1, clear)
            # From a pixel before the image, so its first column is covered too
            band = QRectF(box.left() - 1, 0, box.width() * self.FADE + 1, area.height())
            painter.fillRect(band, fade)
        shade = QLinearGradient(area.left(), 0, area.left() + area.width() * 0.55, 0)
        shade.setColorAt(0, QColor(0, 0, 0, 70))  # a little depth under the title
        shade.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(area, shade)
        painter.end()


def _cover(image: QImage, area: QRectF, top: float) -> QRectF:
    """The part of ``image`` that covers ``area`` without stretching it, its strip starting at
    ``top`` (a share of the height) and anchored on the right, where the players stand."""
    scale = max(area.width() / image.width(), area.height() / image.height())
    width, height = area.width() / scale, area.height() / scale
    return QRectF(
        image.width() - width,
        min(image.height() * top, image.height() - height),
        width,
        height,
    )


_EDGES: dict[tuple[int, float], str] = {}  # by the image's cache key and strip


def edge_colour(image: QImage, top: float) -> str:
    """The average colour of the left edge of the image's strip (the 3% of its width on the
    left), deepened towards the night. Mixed with the league's deep colour, it is the fill the
    image runs into, so the image seems lit from the right."""
    key = (image.cacheKey(), top)
    if key not in _EDGES:
        strip_height = image.width() / 3.7  # the hero's proportions, roughly
        y = min(image.height() * top, image.height() - strip_height)
        edge = image.copy(0, round(y), max(1, image.width() // 33), round(strip_height))
        small = edge.scaled(1, 1, mode=Qt.TransformationMode.SmoothTransformation)
        _EDGES[key] = blend(small.pixelColor(0, 0).name(), "#0A0A0C", 0.3)
    return _EDGES[key]


class StatTile(QFrame):
    """A number read at a glance, its name above it."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.setProperty("role", "card")
        self.value_label = label("–", "stat")
        self.name_label = label(name, "caption")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(2)
        layout.addWidget(self.name_label)
        layout.addWidget(self.value_label)

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
    inside; the most likely outcome is in bold. A legend under the bars names the colours: the
    home win in the league's accent, the draw grey, the away win light, as one family of tones
    rather than three loud colours."""

    ROW_HEIGHT = 40
    LABEL_WIDTH = 150
    LEGEND_HEIGHT = 30

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
            painter.setPen(QColor(current_theme().text))
            painter.drawText(QRectF(0, top, left - 10, 28), LEFT, row.label)
            self._paint_bar(painter, QRectF(left, top, width, 28), row)
        if self.rows:
            self._paint_legend(painter, len(self.rows) * self.ROW_HEIGHT + 8)
        painter.end()

    @staticmethod
    def colours() -> tuple[tuple[str, str], ...]:
        """(fill, text) of the home win, the draw and the away win, in the league's accent."""
        theme = current_theme()
        return ((theme.accent, theme.accent_ink), ("#3A3A42", "#FFFFFF"), ("#E6E6EB", NIGHT))

    def _paint_bar(self, painter: QPainter, area: QRectF, row: BarRow) -> None:
        values = (row.home, row.draw, row.away)
        best = values.index(max(values))
        colours = self.colours()
        outline = QPainterPath()
        outline.addRoundedRect(area, 8, 8)
        painter.save()
        painter.setClipPath(outline)
        x = area.left()
        for index, value in enumerate(values):
            segment = area.width() * value
            last = index == len(values) - 1
            width = area.right() - x if last else max(segment - 2, 0)  # a 2-pixel gap
            box = QRectF(x, area.top(), width, area.height())
            painter.fillRect(box, QColor(colours[index][0]))
            text = percent(value)
            font = QFont(FONT_FAMILY)
            font.setPixelSize(12)
            font.setWeight(QFont.Weight.Bold if index == best else QFont.Weight.Medium)
            if QFontMetrics(font).horizontalAdvance(text) + 10 <= width:
                painter.setFont(font)
                painter.setPen(QColor(colours[index][1]))
                painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
            x += segment
        painter.restore()

    def _paint_legend(self, painter: QPainter, top: float) -> None:
        font = QFont(FONT_FAMILY)
        font.setPixelSize(12)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        x = float(self.LABEL_WIDTH)
        for (colour, _), code in zip(self.colours(), ("H", "D", "A"), strict=True):
            dot = QPainterPath()
            dot.addRoundedRect(QRectF(x, top + 4, 10, 10), 3, 3)
            painter.fillPath(dot, QColor(colour))
            painter.setPen(QColor(current_theme().muted))
            name = OUTCOME_LABELS[code]
            painter.drawText(QPointF(x + 16, top + 13), name)
            x += 16 + metrics.horizontalAdvance(name) + 22


class FormStrip(QWidget):
    """The last results as coloured squares with V, E or Î, oldest first, like a form guide."""

    SQUARE = 24
    GAP = 5
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
        font = QFont(FONT_FAMILY)
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        for index, result in enumerate(self.results):
            box = QRectF(index * (self.SQUARE + self.GAP), 0, self.SQUARE, self.SQUARE)
            path = QPainterPath()
            path.addRoundedRect(box, 7, 7)
            painter.fillPath(path, QColor(self.COLOURS[result]))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, RESULT_LETTERS[result])
        painter.end()


class LeagueButton(QAbstractButton):
    """A league in the side panel: its round flag, its name and its country; the chosen league is
    filled with its accent, as the chosen sport in the references. ``compact`` shows the flag
    alone (a narrow window), with the name as a tooltip."""

    HEIGHT = 56

    def __init__(self, code: str, name: str, country: str, flag: QPixmap) -> None:
        super().__init__()
        self.code = code
        self.setText(name)
        self.country = country
        self._flag = flag
        self.compact = False
        self.setToolTip(f"{name} · {country}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt's name)
        return QSize(60 if self.compact else 220, self.HEIGHT)

    def set_compact(self, compact: bool) -> None:
        if compact != self.compact:
            self.compact = compact
            self.updateGeometry()
            self.update()

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
        area = QRectF(self.rect()).adjusted(12, 4, -12, -4)
        chosen = self.isChecked()
        if chosen or self.underMouse():
            path = QPainterPath()
            path.addRoundedRect(area, 14, 14)
            painter.fillPath(path, QColor(theme.accent if chosen else theme.surface_high))
        flag_size = self._flag.width() / self._flag.devicePixelRatio()
        if self.compact:
            centre = area.center()
            painter.drawPixmap(
                QPointF(centre.x() - flag_size / 2, centre.y() - flag_size / 2), self._flag
            )
            painter.end()
            return
        painter.drawPixmap(QPointF(area.left() + 12, area.center().y() - flag_size / 2), self._flag)
        text_left = area.left() + 12 + flag_size + 12
        name_font = QFont(FONT_FAMILY)
        name_font.setPixelSize(14)
        name_font.setWeight(QFont.Weight.Bold if chosen else QFont.Weight.DemiBold)
        painter.setFont(name_font)
        ink = QColor(theme.accent_ink if chosen else theme.text)
        painter.setPen(ink)
        painter.drawText(QRectF(text_left, area.top() + 8, area.width(), 20), LEFT, self.text())
        country_font = QFont(FONT_FAMILY)
        country_font.setPixelSize(12)
        painter.setFont(country_font)
        secondary = QColor(ink)
        secondary.setAlphaF(0.7)
        painter.setPen(secondary if chosen else QColor(theme.muted))
        painter.drawText(QRectF(text_left, area.top() + 27, area.width(), 18), LEFT, self.country)
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
