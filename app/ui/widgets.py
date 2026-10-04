"""Small display helpers shared by the screens: read-only tables and number formats."""

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

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
