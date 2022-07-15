from __future__ import annotations
from typing import Callable
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtWidgets import QAction
from qtpy.QtCore import Qt, Signal

from ._utils import create_temporal_line_edit

from .._utils import search_name_from_qmenu
from .._table import QBaseTable

class QTabbedTableStack(QtW.QTabWidget):
    """Tab widget used for table stack."""
    
    currentTableChanged = Signal(int)  # index
    itemDropped = Signal(object)  # dropped item info
    itemMoved = Signal(int, int)  # source index, destination index
    tableRenamed = Signal(int, str)  # index
    tableRemoved = Signal(int)  # index
    tablePassed = Signal(object, int, object)  # source widget, tab_id, target widget
    
    def __init__(
        self,
        parent=None,
        tab_position: str = "top",
    ):
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
        self.tabBar().setMouseTracking(True)
        
        self.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self.showContextMenu)
        self.currentChanged.connect(self.currentTableChanged.emit)
        self.tabCloseRequested.connect(self.takeTable)
        self.tabCloseRequested.connect(self.tableRemoved.emit)
        # NOTE: arguments are not (from, to). Bug in Qt??
        self.tabBar().tabMoved.connect(lambda a, b: self.itemMoved.emit(b, a))
        self.tabBarDoubleClicked.connect(self.enterEditingMode)
        self.installContextMenu()
        
        self._line: QtW.QLineEdit | None = None  # temporal QLineEdit for editing tabs
    
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
        # TODO: bug when position is east or south
        if index == -1:
            return None
        return self.tableAtIndex(index)
    
    def moveTable(self, src: int, dst: int):
        """Move table from `src` to `dst`."""
        return self.tabBar().moveTab(src, dst)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        # This override is necessary for accepting drops from files.
        e.accept()
        
        if e.source().parentWidget() is not self:
            return

        self._entering_tab_index = self.indexOf(self.widget(self._moving_tab_index))
        
    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        mime = e.mimeData()
        text = mime.text()
        if text:
            self.itemDropped.emit(text)

        source_widget: QTabbedTableStack = e.source().parentWidget()
        tab_id = source_widget._entering_tab_index
        if source_widget is self:
            return super().dropEvent(e)

        e.setDropAction(Qt.DropAction.MoveAction)
        e.accept()
        
        self.tablePassed.emit(source_widget, tab_id, self)
        return super().dropEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        global_pos = self.mapToGlobal(e.pos())
        tabbar = self.tabBar()
        posInTab = tabbar.mapFromGlobal(global_pos)
        self._moving_tab_index = tabbar.tabAt(e.pos())
        tabrect = self.tabRect(self._moving_tab_index)

        pixmap = QtGui.QPixmap(tabrect.size())
        tabbar.render(pixmap, QtCore.QPoint(), QtGui.QRegion(tabrect))
        mime = QtCore.QMimeData()
        drag = QtGui.QDrag(tabbar)
        drag.setMimeData(mime)
        drag.setPixmap(pixmap)
        cursor = QtGui.QCursor(Qt.CursorShape.OpenHandCursor)
        drag.setHotSpot(e.pos() - posInTab)
        drag.setDragCursor(cursor.pixmap(), Qt.DropAction.MoveAction)
        drag.exec_(Qt.DropAction.MoveAction)
    
    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if self._line is not None:
            self._line.setHidden(True)
        return super().mousePressEvent(e)
    
    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        return super().mouseDoubleClickEvent(e)

    def dragLeaveEvent(self, e: QtGui.QDragLeaveEvent):
        e.accept()
        return None
    
    def tabRect(self, index: int):
        """Get QRect of the tab at index."""
        rect = self.tabBar().tabRect(index)
        
        # NOTE: East/South tab returns wrong value (Bug in Qt?)
        if self.tabPosition() == QtW.QTabWidget.TabPosition.East:
            w = self.rect().width() - rect.width()
            rect.translate(w, 0)
        elif self.tabPosition() == QtW.QTabWidget.TabPosition.South:
            h = self.rect().height() - rect.height()
            rect.translate(0, h)
    
        return rect

    def enterEditingMode(self, index: int):
        """Enter edit table name mode."""
        rect = self.tabRect(index)

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
        
        @self.registerAction("Copy all")
        def _copy(index: int):
            table = self.tableAtIndex(index)
            h, w = table.tableShape()
            table.setSelections([(slice(0, h), slice(0, w))])
            table.copyToClipboard(headers=True)
            table.setSelections([])
            
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
        self._qt_context_menu.execAtIndex(QtGui.QCursor().pos(), index)
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
