from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

if TYPE_CHECKING:
    from ._table_base import _QTableViewEnhanced

# Wrapper widgets that can be used to wrap a QTableView


class QTableDualView(QtW.QSplitter):
    """Dual view of the same table."""

    def __init__(
        self, table: _QTableViewEnhanced, orientation=Qt.Orientation.Horizontal
    ):
        from ._table_base import _QTableViewEnhanced

        super().__init__(orientation)
        self.setChildrenCollapsible(False)

        second = _QTableViewEnhanced()
        second.setModel(table.model())
        second.setSelectionModel(table.selectionModel())
        second.setItemDelegate(table.itemDelegate())
        second.setZoom(table.zoom())

        self.addWidget(table)
        self.setStretchFactor(0, 1)
        self.addWidget(second)
        self.setStretchFactor(1, 1)

        self._first = table
        self._second = second
