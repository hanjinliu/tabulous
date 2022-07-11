from __future__ import annotations
import warnings
from qtpy import QtCore
from qtpy.QtCore import Qt, Signal
import pandas as pd

# https://ymt-lab.com/post/2020/pyqt5-qtableview-pandas-qabstractitemmodel/

class AbstractDataFrameModel(QtCore.QAbstractTableModel):
    dataEdited = Signal(int, int, object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._df = pd.DataFrame([])

    @property
    def df(self) -> pd.DataFrame:
        return self._df
    
    def updateValue(self, r, c, val):
        # pandas warns but no problem
        with warnings.catch_warnings():
            self._df.iloc[r, c] = val
    
    def data(self, index: QtCore.QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QtCore.QVariant()
        if role == Qt.ItemDataRole.EditRole or role == Qt.ItemDataRole.DisplayRole:
            r, c = index.row(), index.column()
            if r < self.df.shape[0] and c < self.df.shape[1]:
                return str(self.df.iat[r, c])
            return ""
        return QtCore.QVariant()

    def flags(self, index):
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
    
    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole
    ):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if section < self.df.columns.size:
                return self.df.columns[section]
            else:
                return None
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            if section < self.df.index.size:
                return self.df.index[section]
            else:
                return None

    def setData(self, index: QtCore.QModelIndex, value, role):
        if not index.isValid():
            return False
        if role != Qt.ItemDataRole.EditRole:
            return False
        r, c = index.row(), index.column()
        self.dataEdited.emit(r, c, value)
        return True

class DataFrameModel(AbstractDataFrameModel):
    
    @property
    def df(self) -> pd.DataFrame:
        return self._df
    
    @df.setter
    def df(self, data: pd.DataFrame):
        if data is self._df:
            return
        old_shape = self.df.shape
        new_shape = data.shape
        dr = new_shape[0] - old_shape[0]
        dc = new_shape[1] - old_shape[1]
        if dr > 0:
            self.beginInsertRows(QtCore.QModelIndex(), old_shape[0], old_shape[0]+dr-1)
            self.insertRows(old_shape[0], dr, QtCore.QModelIndex())
            self.endInsertRows()
        elif dr < 0:
            self.beginRemoveRows(QtCore.QModelIndex(), old_shape[0]+dr, old_shape[0]-1)
            self.removeRows(old_shape[0]+dr, -dr, QtCore.QModelIndex())
            self.endRemoveRows()
        if dc > 0:
            self.beginInsertColumns(QtCore.QModelIndex(), old_shape[1], old_shape[1]+dc-1)
            self.insertColumns(old_shape[1], dc, QtCore.QModelIndex())
            self.endInsertColumns()
        elif dc < 0:
            self.beginRemoveColumns(QtCore.QModelIndex(), old_shape[1]+dc, old_shape[1]-1)
            self.removeColumns(old_shape[1]+dc, -dc, QtCore.QModelIndex())
            self.endRemoveColumns()
        
        self._df = data
    
    def rowCount(self, parent=None):
        return self.df.shape[0]

    def columnCount(self, parent=None):
        return self.df.shape[1]

MAX_ROW_SIZE = 1800
MAX_COLUMN_SIZE = 800

class SpreadSheetModel(AbstractDataFrameModel):
    
    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @df.setter
    def df(self, data: pd.DataFrame):
        self._df = data

    def rowCount(self, parent=None):
        return MAX_ROW_SIZE

    def columnCount(self, parent=None):
        return MAX_COLUMN_SIZE
