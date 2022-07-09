from __future__ import annotations
from typing import Callable
from qtpy.QtWidgets import QAction, QMenu
from qtpy.QtCore import Signal, QPoint
from .._table import QTableLayer
from .._utils import search_name_from_qmenu

class QTabContextMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_index = None
        
    def execAtIndex(self, pos: QPoint, index: int):
        """Execute contextmenu at index."""
        self._current_index = index
        try:
            self.exec_(pos)
        finally:
            self._current_index = None
        return None

class _QTableStackBase:
    currentTableChanged = Signal(int)
    itemDropped = Signal(object)
    itemMoved = Signal(int, int)
    tableRenamed = Signal(int, str)
    tableRemoved = Signal(int)

    _qt_context_menu: QTabContextMenu
        
    def installContextMenu(self):
        """Install the default contextmenu."""
        self._qt_context_menu = QTabContextMenu(self)
        self.registerAction("Rename")(self.enterEditingMode)
        @self.registerAction("Delete")
        def _delete(index: int):
            self.takeTable(index)
            self.tableRemoved.emit(index)
    
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
    
    def tableAt(self, pos: QPoint) -> QTableLayer | None:
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
    
    def enterEditingMode(self, index: int):
        """Enter edit table name mode."""
        raise NotImplementedError()

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
    
    def showContextMenu(self, pos: QPoint) -> None:
        """Execute contextmenu."""
        table = self.tableAt(pos)
        if table is None:
            return
        index = self.tableIndex(table)
        self._qt_context_menu.execAtIndex(self.mapToGlobal(pos), index)
        return