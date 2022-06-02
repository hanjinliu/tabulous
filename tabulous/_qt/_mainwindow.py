from __future__ import annotations
from operator import index
from typing import TYPE_CHECKING
import pandas as pd
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from ._stack import QTableStack
from ._tablist import QTabList
from ._table import QTableLayer

class QMainWindow(QtW.QMainWindow):
    def __init__(self):
        super().__init__()
        self._split = QtW.QSplitter(orientation=Qt.Horizontal, parent=self)
        self.setCentralWidget(self._split)
        self._tablist = QTabList(self._split)
        self._tablestack = QTableStack(parent=self)
        self._split.addWidget(self._tablist)
        self._split.addWidget(self._tablestack)
        
        self._tablist.selectionChangedSignal.connect(self.setStackIndex)
    
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