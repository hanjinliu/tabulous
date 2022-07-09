from __future__ import annotations
from typing import TYPE_CHECKING
import weakref
from qtpy import QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt, Signal
import pandas as pd

# https://ymt-lab.com/post/2020/pyqt5-qtableview-pandas-qabstractitemmodel/

class AbstractDataFrameModel(QtCore.QAbstractTableModel):
    dataEdited = Signal(int, int, object)
    
    def __init__(self, parent=None, data: pd.DataFrame=None):
        super().__init__(parent)
        self.df = data

    def rowCount(self, parent=None):
        return self.df.shape[0]

    def columnCount(self, parent=None):
        return self.df.shape[1]
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QtCore.QVariant()
        if role == Qt.ItemDataRole.EditRole or role == Qt.ItemDataRole.DisplayRole:
            return self.df.iat[index.row(), index.column()]
        return QtCore.QVariant()

    def flags(self, index):
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.df.columns[section]
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return self.df.index[section]

    def setData(self, index: QtCore.QModelIndex, value, role):
        if not index.isValid():
            return False
        if role != Qt.ItemDataRole.EditRole:
            return False
        row = index.row()
        column = index.column()
        self.dataEdited.emit(row, column, value)
        return True