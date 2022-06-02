from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, QEvent

from ._stack import QTableStack
from ._tablist import QTabList
from ._table import QTableLayer

if TYPE_CHECKING:
    from ..widgets import TableViewer

class QMainWindow(QtW.QMainWindow):
    _table_viewer: TableViewer
    _instances: list['QMainWindow'] = []
    
    def __init__(self):
        super().__init__()
        self._split = QtW.QSplitter(orientation=Qt.Horizontal, parent=self)
        self.setCentralWidget(self._split)
        self._tablist = QTabList(self._split)
        self._tablestack = QTableStack(parent=self)
        self._split.addWidget(self._tablist)
        self._split.addWidget(self._tablestack)
        
        self._tablist.selectionChangedSignal.connect(self.setStackIndex)
        
        QMainWindow._instances.append(self)
    
    def addTable(self, table: QTableLayer, name: str) -> QTableLayer:
        if not isinstance(table, QTableLayer):
            raise TypeError(f"Cannot add {type(table)}.")
        self._tablist.addTable(table, name)
        self._tablestack.addWidget(table)
        return table
    
    def removeTable(self, index: int):
        table = self._tablist.takeTable(index)
        self._tablestack.removeWidget(table)
    
    def renameTable(self, index: int, name: str):
        item = self._tablist.item(index)
        tab = self._tablist.itemWidget(item)
        tab.rename(name)
        
    def setStackIndex(self, index: int) -> None:
        self._tablestack.setCurrentIndex(index)
    
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