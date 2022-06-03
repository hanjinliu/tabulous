from __future__ import annotations
from typing import TYPE_CHECKING
import weakref
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal
from ._table import QTableLayer

class QTabList(QtW.QListWidget):
    selectionChangedSignal = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
    
    def addTable(self, table: QTableLayer, name: str = "None"):
        item = QTabListItem(table, parent=self)
        self.addItem(item)
        tab = QTab(parent=self, text=name)
        self.setItemWidget(item, tab)
        return tab
        
    def takeTable(self, index: int) -> QTableLayer:
        item = self.takeItem(index)
        return item.table
    
    def renameTable(self, index: int, name: str):
        item = self.item(index)
        tab = self.itemWidget(item)
        tab.setText(name)
        return None
    
    def tableIndex(self, table: QTableLayer) -> int:
        for i in range(self.count()):
            if table is self.item(i).table:
                return i
        else:
            raise ValueError("Table not found.")
    
    if TYPE_CHECKING:
        def item(self, index: int) -> QTabListItem: ...
        def takeItem(self, index: int) -> QTabListItem: ...
        def itemWidget(self, item: QTabListItem) -> QTab: ...
    
    def selectionChanged(self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection) -> None:
        index = selected.indexes()[0].row()
        self.selectionChangedSignal.emit(index)
        item = self.item(index)
        widget = self.itemWidget(item)
        widget.setHighlight(True)
        for i in deselected.indexes():
            item = self.item(i.row())
            widget = self.itemWidget(item)
            widget.setHighlight(False)
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

class QTab(QtW.QLabel):
    renamed = Signal(str)
    
    def __init__(self, parent=None, text: str = ""):
        super().__init__(parent=parent)
        self.setText(text)
    
    def setHighlight(self, value: bool):
        font = self.font()
        font.setBold(value)
        self.setFont(font)
    
    def setText(self, text: str) -> None:
        super().setText(text)
    
    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent) -> None:
        line = QtW.QLineEdit(parent=self)

        # set geometry
        edit_geometry = line.geometry()
        edit_geometry.setWidth(self.width())
        line.setGeometry(edit_geometry)
        
        line.setText(self.text())
        line.setHidden(False)
        line.setFocus()
        line.selectAll()
        
        self._line = line # we have to retain the pointer, otherwise got error sometimes
        
        @self._line.editingFinished.connect
        def _():
            self._line.setHidden(True)
            self.renamed.emit(self._line.text())
        
        return super().mouseDoubleClickEvent(a0)