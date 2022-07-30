from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, Signal

if TYPE_CHECKING:
    from ._table_base import QBaseTable

# Wrapper widgets that can be used to wrap a QTableView


class QTableGroup(QtW.QSplitter):
    """Split view of two tables."""

    focusChanged = Signal(int)

    def __init__(self, tables: list[QBaseTable], orientation=Qt.Orientation.Horizontal):
        super().__init__(orientation)
        self.setChildrenCollapsible(False)

        self._tables: list[QBaseTable] = []
        for i, table in enumerate(tables):
            table_copy = table.copy(link=True)
            table_copy._qtable_view.focusedSignal.connect(
                lambda: self.focusChanged.emit(self.focusedIndex())
            )
            self.addWidget(table_copy)
            self.setStretchFactor(i, 1)
            self._tables.append(table)

    def copy(self) -> QTableGroup:
        """Make a copy of this widget."""
        copy = self.__class__(self.tables, self.orientation())
        return copy

    @property
    def tables(self) -> list[QBaseTable]:
        return self._tables.copy()

    def pop(self, index: int = -1) -> QBaseTable:
        if index < 0:
            index += self.count()
        table = self.widget(index)
        table.deleteLater()
        return self.tables[index]

    def tableIndex(self, table: QBaseTable) -> int:
        model = table.model()
        for t in self.tables:
            if t.model() is model:
                return t
        raise ValueError("Table not found.")

    def focusedIndex(self) -> int:
        """Return the index of the currently focused table."""
        for i in range(self.count()):
            if self.tableHasFocus(i):
                return i
        return -1

    def setFocusedIndex(self, index: int) -> None:
        """Set the focused widget to the table at index."""
        return self.widget(index)._qtable_view.setFocus()

    def focusedTable(self) -> QBaseTable | None:
        """Return the currently focused table widget."""
        i = self.focusedIndex()
        if i < 0:
            return None
        return self.tables[i]

    def tableHasFocus(self, index: int) -> bool:
        """True if the table at index has focus."""
        return self.widget(index)._qtable_view.hasFocus()

    def __eq__(self, other: QTableGroup) -> bool:
        if not isinstance(other, QTableGroup):
            return False
        # NOTE: This should be safe. Table groups derived from the same ancestor
        # will always have exclusively the same set of tables.
        return self.tables[0].model() is other.tables[0].model()

    if TYPE_CHECKING:

        def widget(self, index: int) -> QBaseTable:
            ...
