from __future__ import annotations
from typing import TYPE_CHECKING
import weakref
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt

if TYPE_CHECKING:
    import pandas as pd

class QTreeHeaderView(QtW.QHeaderView):
    def __init__(self, orientation: Qt.Orientation, parent: QtW.QWidget | None = None) -> None:
        super().__init__(orientation, parent)
    
    def paintSection(self, painter: QtGui.QPainter, rect: QtCore.QRect, logicalIndex: int) -> None:
        return super().paintSection(painter, rect, logicalIndex)

class QTableHeaderItem(QtW.QTableWidgetItem):
    def __init__(self, parent, item_parent=None):
        super().__init__(parent)
        self._item_parent = item_parent
        
    def insertChild(self):
        ...
    
    def children(self):
        ...
    
   
class HeaderModel(QtW.QAbstractItemView):
    
    ...
    
    # TODO: 
    # df0.columns.levels
    # Out[12]: FrozenList([['b', 'c', 'x'], ['mean', 'std', '']])

    # mi = df0.columns

    # mi.get_indexer
    # Out[14]: 
    # <bound method Index.get_indexer of MultiIndex([('b', 'mean'),
    #             ('b',  'std'),
    #             ('c', 'mean'),
    #             ('c',  'std'),
    #             ('x',     '')],
    #            )>

    # mi.get_level_values(0)
    # Out[15]: Index(['b', 'b', 'c', 'c', 'x'], dtype='object')

    # mi.get_level_values(1)
    # Out[16]: Index(['mean', 'std', 'mean', 'std', ''], dtype='object')

    # mi.nlevels
    # Out[17]: 2
