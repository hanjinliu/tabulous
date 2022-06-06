from __future__ import annotations
from typing import TYPE_CHECKING, Callable, TypeVar
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtWidgets import QAction
from qtpy.QtCore import Qt, QEvent

from ._stack import QTableStack
from ._tablist import QTabList
from ._table import QTableLayer
from ._utils import search_name_from_qmenu

if TYPE_CHECKING:
    from ..widgets import TableViewer
    from typing_extensions import ParamSpec
    _P = ParamSpec("_P")

_R = TypeVar("_R")

class QMainWindow(QtW.QMainWindow):
    _table_viewer: TableViewer
    _instances: list['QMainWindow'] = []
    
    def __init__(self):
        super().__init__()
        self._split = QtW.QSplitter(orientation=Qt.Orientation.Horizontal, parent=self)
        self.setCentralWidget(self._split)
        self._tablist = QTabList(self._split)
        self._tablestack = QTableStack(parent=self)
        self._split.addWidget(self._tablist)
        self._split.addWidget(self._tablestack)
        
        self._tablist.selectionChangedSignal.connect(self._on_selection_change)

        QMainWindow._instances.append(self)
    
    def _on_selection_change(self, i: int):
        qtable = self._tablist.tableAtIndex(i)
        self._tablestack.setCurrentWidget(qtable)
        return None
    
    def addTable(self, table: QTableLayer, name: str):
        if not isinstance(table, QTableLayer):
            raise TypeError(f"Cannot add {type(table)}.")
        qtab = self._tablist.addTable(table=table, name=name)
        self._tablestack.addWidget(table)
        return qtab
    
    def removeTable(self, index: int):
        table = self._tablist.takeTable(index)
        for child in self._tablestack.children():
            if child is table:
                child.setParent(None)
    
    def renameTable(self, table: QTableLayer, name: str):
        index = self._tablist.tableIndex(table)
        item = self._tablist.item(index)
        tab = self._tablist.itemWidget(item)
        tab.setText(name)
    
    def addDockWidget(
        self, 
        qwidget: QtW.QWidget,
        *,
        name: str = "",
        area: str = "right",
        allowed_areas: list[str] = None,
    ):
        from .._qt._dockwidget import QtDockWidget

        name = name or qwidget.objectName()
        dock = QtDockWidget(
            self,
            qwidget,
            name=name.replace("_", " "),
            area=area,
            allowed_areas=allowed_areas,
        )

        super().addDockWidget(QtDockWidget.areas[area], dock)
        return dock
            
    def stackIndex(self) -> int:
        return self._tablestack.currentIndex()
    
    def setStackIndex(self, index: int) -> None:
        self._tablist.setCurrentRow(index)
    
    @classmethod
    def currentViewer(cls):
        window = cls._instances[-1] if cls._instances else None
        return window._table_viewer if window else None
    
    def event(self, e):
        if e.type() == QEvent.Close:
            # when we close the MainWindow, remove it from the instances list
            try:
                QMainWindow._instances.remove(self)
            except ValueError:
                pass
        if e.type() in {QEvent.WindowActivate, QEvent.ZOrderChange}:
            # upon activation or raise_, put window at the end of _instances
            try:
                inst = QMainWindow._instances
                inst.append(inst.pop(inst.index(self)))
            except ValueError:
                pass
        return super().event(e)

    def registerAction(self, location: str) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
        locs = location.split(">")
        if len(locs) < 2:
            raise ValueError("Location must be 'XXX>YYY>ZZZ' format.")
        menu = self.menuBar()
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
            action.triggered.connect(f)
            menu.addAction(action)
            return f
        return wrapper
