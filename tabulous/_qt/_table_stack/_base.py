from __future__ import annotations
from typing import TYPE_CHECKING, Callable
import weakref
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtWidgets import QAction, QMenu
from qtpy.QtCore import Qt, Signal
from .._table import QTableLayer
from .._utils import search_name_from_qmenu

class QTabContextMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_table = None
        
    def execOnTable(self, pos: QtCore.QPoint, table: QTableLayer):
        if self._current_table is not None:
            self.exec_(pos)
        return None

class _QTableStackBase:
    currentTableChanged = Signal(int)
    itemDropped = Signal(object)
    itemMoved = Signal(int, int)
    tableRenamed = Signal(int, str)
    tableRemoved = Signal(int)

    _qt_context_menu: QTabContextMenu
    
    def addTable(self, table: QTableLayer, name: str = "None"):
        """Add `table` to stack as name `name`."""
        raise NotImplementedError()
        
    def takeTable(self, index: int) -> QTableLayer:
        """Remove table at `index` and return it."""
        raise NotImplementedError()
    
    def renameTable(self, index: int, name: str):
        """Rename table at `index` to `name`."""
        raise NotImplementedError()
    
    def tableIndex(self, table: QTableLayer) -> int:
        """Get the index of `table`."""
        raise NotImplementedError()
    
    def tableAtIndex(self, i: int) -> QTableLayer:
        """Get the table at `i`."""
        raise NotImplementedError()
    
    def tableAt(self, pos: QtCore.QPoint) -> QTableLayer | None:
        """Return table at a mouse position."""
        raise NotImplementedError()
    
    def moveTable(self, src: int, dst: int):
        """Move table from `src` to `dst`."""
        raise NotImplementedError()

    def currentIndex(self):
        """Return the current active table index."""
        raise NotImplementedError()

    def setCurrentIndex(self, i: int):
        """Set the current active table index and update the widget."""
        raise NotImplementedError()
    
    def registerAction(self, location: str):
        # TODO: how to pass current table to the registered function?
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
                lambda: f(self._qt_context_menu._current_table)
            )
            menu.addAction(action)
            return f
        return wrapper
    
    def showContextMenu(self, pos: QtCore.QPoint) -> None:
        """Execute contextmenu."""
        item = self.itemAt(pos)
        if item is None:
            return
        self._qt_context_menu.execOnTable(self.mapToGlobal(pos), item)
        return
