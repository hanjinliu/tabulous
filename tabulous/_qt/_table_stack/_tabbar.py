from __future__ import annotations
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtWidgets import QMenu
from qtpy.QtCore import Signal

from ._base import _QTableStackBase
from ._utils import create_temporal_line_edit

from .._table import QTableLayer

class QTabbedTableStack(QtW.QTabWidget, _QTableStackBase):
    currentTableChanged = Signal(int)
    itemDropped = Signal(object)
    itemMoved = Signal(int, int)
    tableRenamed = Signal(int, str)
    tableRemoved = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setAcceptDrops(True)
        self.setTabsClosable(True)
        
        self._tables: list[QTableLayer] = []
        self._qt_context_menu = QMenu()
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.currentChanged.connect(self.currentTableChanged.emit)
        self.tabCloseRequested.connect(self.takeTable)
        self.tabCloseRequested.connect(self.tableRemoved.emit)
        self.tabBar().tabMoved.connect(self.itemMoved.emit)
    
    def addTable(self, table: QTableLayer, name: str = "None"):
        self.addTab(table, name)
        self._tables.append(table)
        
    def takeTable(self, index: int) -> QTableLayer:
        self.removeTab(index)
        del self._tables[index]
    
    def renameTable(self, index: int, name: str):
        self.setTabText(index, name)

    def tableIndex(self, table: QTableLayer) -> int:
        self._tables.index(table)
    
    def tableAtIndex(self, i: int) -> QTableLayer:
        return self._tables[i]
    
    def tableAt(self, pos: QtCore.QPoint) -> QTableLayer | None:
        """Return table at position."""
        index = self.tabBar().tabAt(pos)
        if index == -1:
            return None
        return self.tableAtIndex(index)
    
    def moveTable(self, src: int, dst: int):
        self.tabBar().moveTab(src, dst)
        if src < dst:
            dst -= 1
        table = self._tables.pop(src)
        self._tables.insert(table)

    def dropEvent(self, a0: QtGui.QDropEvent) -> None:
        mime = a0.mimeData()
        self.itemDropped.emit(mime.text())
        return super().dropEvent(a0)

    def enterEditingMode(self, index: int):
        rect = self.tabBar().tabRect(index)
        line = QtW.QLineEdit(parent=self)

        # set geometry
        line = create_temporal_line_edit(rect, self, self.tabText(index))
        self._line = line
        
        @self._line.editingFinished.connect
        def _():
            self._line.setHidden(True)
            text = self._line.text()
            self.setTabText(text)
            self.tableRenamed.emit(index, text)
        return None

