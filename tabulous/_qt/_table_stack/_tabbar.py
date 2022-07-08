from __future__ import annotations
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal

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
        self.setMovable(True)
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.currentChanged.connect(self.currentTableChanged.emit)
        self.tabCloseRequested.connect(self.takeTable)
        self.tabCloseRequested.connect(self.tableRemoved.emit)
        # NOTE: arguments are not (from, to). Bug in Qt??
        self.tabBar().tabMoved.connect(lambda a, b: self.itemMoved.emit(b, a))
        self.tabBarDoubleClicked.connect(self.enterEditingMode)
        self.installContextMenu()
    
    def addTable(self, table: QTableLayer, name: str = "None"):
        """Add `table` to stack as name `name`."""
        self.addTab(table, name)
        self.tabBar().setTabData(self.count() - 1, table)
        return None
        
    def takeTable(self, index: int) -> QTableLayer:
        """Remove table at `index` and return it."""
        return self.removeTab(index)
    
    def renameTable(self, index: int, name: str):
        """Rename table at `index` to `name`."""
        return self.setTabText(index, name)

    def tableIndex(self, table: QTableLayer) -> int:
        """Get the index of `table`."""
        for i in range(self.count()):
            data = self.tabBar().tabData(i)
            if data is table:
                break
        else:
            raise ValueError(f"Table {table!r} not found.")
        return i
    
    def tableAtIndex(self, i: int) -> QTableLayer:
        """Get the table at `i`."""
        return self.tabBar().tabData(i)
    
    def tableAt(self, pos: QtCore.QPoint) -> QTableLayer | None:
        """Return table at position."""
        index = self.tabBar().tabAt(pos)
        if index == -1:
            return None
        return self.tableAtIndex(index)
    
    def moveTable(self, src: int, dst: int):
        """Move table from `src` to `dst`."""
        return self.tabBar().moveTab(src, dst)

    def dropEvent(self, a0: QtGui.QDropEvent) -> None:
        mime = a0.mimeData()
        self.itemDropped.emit(mime.text())
        return super().dropEvent(a0)

    def enterEditingMode(self, index: int):
        """Enter edit table name mode."""
        rect = self.tabBar().tabRect(index)
        line = QtW.QLineEdit(parent=self)

        # set geometry
        line = create_temporal_line_edit(rect, self, self.tabText(index))
        self._line = line
        
        @self._line.editingFinished.connect
        def _():
            self._line.setHidden(True)
            text = self._line.text()
            self.setTabText(index, text)
            self.tableRenamed.emit(index, text)
        return None

