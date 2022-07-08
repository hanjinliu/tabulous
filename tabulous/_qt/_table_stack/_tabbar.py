from __future__ import annotations
from typing import TYPE_CHECKING, Callable
import weakref
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtWidgets import QAction, QMenu
from qtpy.QtCore import Qt, Signal

from ._base import _QTableStackBase

from .._table import QTableLayer

class QTabbedTableStack(QtW.QTabWidget, _QTableStackBase):
    currentTableChanged = Signal(int)
    itemMoved = Signal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        
        self._tables: list[QTableLayer] = []
        self._qt_context_menu = QMenu()
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.currentChanged.connect(self.currentTableChanged.emit)
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

    # TODO: editable tab names
    