from __future__ import annotations
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt
import pandas as pd


class QTreeHeaderModel(QtCore.QAbstractTableModel):
    def __init__(
        self,
        df: pd.DataFrame,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._df = df
        self._orientation = orientation

    def columnCount(self, parent=None):
        if self._orientation == Qt.Orientation.Horizontal:
            return self._df.columns.shape[0]
        else:  # Vertical
            return self._df.index.nlevels

    def rowCount(self, parent=None):
        if self._orientation == Qt.Orientation.Horizontal:
            return self._df.columns.nlevels
        else:
            return self._df.index.shape[0]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        row = index.row()
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.ToolTipRole:

            if self._orientation == Qt.Orientation.Horizontal:

                if isinstance(self._df.columns, pd.MultiIndex):
                    return str(self._df.columns[col][row])
                else:
                    return str(self._df.columns[col])

            else:

                if isinstance(self._df.index, pd.MultiIndex):
                    return str(self._df.index[row][col])
                else:
                    return str(self._df.index[row])


class QTreeHeaderView(QtW.QHeaderView):
    def __init__(
        self,
        df: pd.DataFrame,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        parent: QtW.QWidget | None = None,
    ) -> None:
        super().__init__(orientation, parent)
        self.setModel(QTreeHeaderModel(df, orientation))

    def paintSection(
        self, painter: QtGui.QPainter, rect: QtCore.QRect, logicalIndex: int
    ) -> None:
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
