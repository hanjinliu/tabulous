from __future__ import annotations
from typing import TYPE_CHECKING
import weakref
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt, Signal
from ._table import QTableLayer

class QTabList(QtW.QListWidget):
    selectionChangedSignal = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtW.QAbstractItemView.SingleSelection)
    
    def addTable(self, table: QTableLayer):
        self.addItem(QTabListItem(table, parent=self))
    
    def item(self, index: int) -> QTabListItem:
        return super().item(index)
    
    def selectionChanged(self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection) -> None:
        index = selected.indexes()[0].row()
        self.selectionChangedSignal.emit(index)
        return super().selectionChanged(selected, deselected)

class QTabListItem(QtW.QListWidgetItem):
    def __init__(self, table: QTableLayer, parent=None):
        if not isinstance(table, QTableLayer):
            raise TypeError(f"Cannot add {type(table)}")
        super().__init__(parent=parent)
        self._table_ref = weakref.ref(table)
    
    @property
    def table(self) -> QTableLayer:
        out = self._table_ref()
        if out is None:
            raise ValueError("QTableLayer object is deleted.")
        return out