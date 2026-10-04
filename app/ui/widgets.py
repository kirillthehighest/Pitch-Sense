"""Small display helpers shared by the screens: read-only tables, charts and number formats."""

from collections.abc import Sequence

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

OUTCOME_NAMES = {"H": "Home win", "D": "Draw", "A": "Away win"}


def make_table(headers: Sequence[str], stretch_column: int | None = None) -> QTableWidget:
    """A read-only table; ``stretch_column`` (usually a name column) takes the spare width."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(list(headers))
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.verticalHeader().setVisible(False)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setStretchLastSection(False)
    if stretch_column is not None:
        header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)
    return table


def fill_table(table: QTableWidget, rows: Sequence[Sequence[str]], fit: bool = False) -> None:
    """Replace the table's rows; numbers are right-aligned.

    With ``fit`` the table becomes exactly as tall as its rows, for short tables whose rows
    should all be visible without scrolling.
    """
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column, text in enumerate(row):
            item = QTableWidgetItem(text)
            if _looks_numeric(text):
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row_index, column, item)
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


def percent(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}%}"


def number(value: float | None, digits: int = 4) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _looks_numeric(text: str) -> bool:
    """True for numbers such as 12, -0.0073, +0.0056 or 53.4%; False for 2010-11 or 2-1."""
    try:
        float(text.replace("%", "").strip())
    except ValueError:
        return False
    return True
