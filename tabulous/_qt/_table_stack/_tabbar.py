from __future__ import annotations
from typing import Callable
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtWidgets import QAction
from qtpy.QtCore import Qt, Signal

from ._utils import create_temporal_line_edit

from .._utils import search_name_from_qmenu
from .._table import QBaseTable

class QTabbedTableStack(QtW.QTabWidget):
    currentTableChanged = Signal(int)
    itemDropped = Signal(object)
    itemMoved = Signal(int, int)
    tableRenamed = Signal(int, str)
    tableRemoved = Signal(int)
    
    def __init__(self, parent=None, tab_position="top"):
        super().__init__(parent)
        if tab_position == "top":
            pass
        elif tab_position == "left":
            from ._sidebar import QLeftSideBar
            self.setTabBar(QLeftSideBar(self))
            self.setTabPosition(QtW.QTabWidget.TabPosition.West)
        elif tab_position == "bottom":
            self.setTabPosition(QtW.QTabWidget.TabPosition.South)
        elif tab_position == "right":
            from ._sidebar import QRightSideBar
            self.setTabBar(QRightSideBar(self))
            self.setTabPosition(QtW.QTabWidget.TabPosition.East)
        else:
            raise ValueError(f"Unknown position {tab_position!r}.")
            
        # self.setMinimumSize(600, 400)
        self.setAcceptDrops(True)
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
    
    def addTable(self, table: QBaseTable, name: str = "None"):
        """Add `table` to stack as name `name`."""
        self.addTab(table, name)
        self.tabBar().setTabData(self.count() - 1, table)
        return None
        
    def takeTable(self, index: int) -> QBaseTable:
        """Remove table at `index` and return it."""
        return self.removeTab(index)
    
    def renameTable(self, index: int, name: str):
        """Rename table at `index` to `name`."""
        return self.setTabText(index, name)

    def tableIndex(self, table: QBaseTable) -> int:
        """Get the index of `table`."""
        for i in range(self.count()):
            data = self.tabBar().tabData(i)
            if data is table:
                break
        else:
            raise ValueError(f"Table {table!r} not found.")
        return i
    
    def tableAtIndex(self, i: int) -> QBaseTable:
        """Get the table at `i`."""
        return self.tabBar().tabData(i)
    
    def tableAt(self, pos: QtCore.QPoint) -> QBaseTable | None:
        """Return table at position."""
        index = self.tabBar().tabAt(pos)
        if index == -1:
            return None
        return self.tableAtIndex(index)
    
    def moveTable(self, src: int, dst: int):
        """Move table from `src` to `dst`."""
        return self.tabBar().moveTab(src, dst)

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent) -> None:
        # This override is necessary for accepting drops from files.
        a0.accept()
        
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
    
    def installContextMenu(self):
        """Install the default contextmenu."""
        self._qt_context_menu = QTabContextMenu(self)
        self.registerAction("Rename")(self.enterEditingMode)
        @self.registerAction("Delete")
        def _delete(index: int):
            self.takeTable(index)
            self.tableRemoved.emit(index)

    def registerAction(self, location: str):
        locs = location.split(">")
        menu = self._qt_context_menu
        for loc in locs[:-1]:
            a = search_name_from_qmenu(menu, loc)
            if a is None:
                menu = menu.addMenu(loc)
            else:
                menu = a.menu()
                if menu is None:
                    i = locs.index(loc)
                    err_loc = ">".join(locs[:i])
                    raise TypeError(f"{err_loc} is not a menu.")
                
        def wrapper(f: Callable):
            action = QAction(locs[-1], self)
            action.triggered.connect(
                lambda: f(self._qt_context_menu._current_index)
            )
            menu.addAction(action)
            return f
        return wrapper
    
    def showContextMenu(self, pos: QtCore.QPoint) -> None:
        """Execute contextmenu."""
        table = self.tableAt(pos)
        if table is None:
            return
        index = self.tableIndex(table)
        self._qt_context_menu.execAtIndex(self.mapToGlobal(pos), index)
        return


class QTabContextMenu(QtW.QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_index = None
        
    def execAtIndex(self, pos: QtCore.QPoint, index: int):
        """Execute contextmenu at index."""
        self._current_index = index
        try:
            self.exec_(pos)
        finally:
            self._current_index = None
        return None
