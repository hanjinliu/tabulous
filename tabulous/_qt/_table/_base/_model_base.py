from __future__ import annotations
import warnings
from qtpy import QtCore, QtGui
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
    
    def data(
        self,
        index: QtCore.QModelIndex, 
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return QtCore.QVariant()
        if role == Qt.ItemDataRole.EditRole or role == Qt.ItemDataRole.DisplayRole:
            r, c = index.row(), index.column()
            if r < self.df.shape[0] and c < self.df.shape[1]:
                return str(self.df.iat[r, c])
            return ""
        elif role == Qt.ItemDataRole.TextColorRole:
            r, c = index.row(), index.column()
            if r < self.df.shape[0] and c < self.df.shape[1]:
                val = self.df.iat[r, c]
                if pd.isna(val):
                    return QtGui.QColor(Qt.GlobalColor.gray)
            return QtCore.QVariant()    
        return QtCore.QVariant()

    def flags(self, index):
        return (
            Qt.ItemFlag.ItemIsEditable | 
            Qt.ItemFlag.ItemIsEnabled |
            Qt.ItemFlag.ItemIsSelectable
        )
    
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

    def setData(self, index: QtCore.QModelIndex, value, role) -> bool:
        if not index.isValid():
            return False
        if role != Qt.ItemDataRole.EditRole:
            return False
        r, c = index.row(), index.column()
        self.dataEdited.emit(r, c, value)
        return True

    def setShape(self, nrow: int, ncol: int):
        """Set table shape."""
        r0, c0 = self.rowCount(), self.columnCount()
        dr = nrow - r0
        dc = ncol - c0
        
        # Adjust rows
        if dr > 0:
            self.beginInsertRows(QtCore.QModelIndex(), r0, r0 + dr - 1)
            self.insertRows(r0, dr, QtCore.QModelIndex())
            self.endInsertRows()
        elif dr < 0:
            self.beginRemoveRows(QtCore.QModelIndex(), r0 + dr, r0 - 1)
            self.removeRows(r0 + dr, -dr, QtCore.QModelIndex())
            self.endRemoveRows()
        
        # Adjust columns
        if dc > 0:
            self.beginInsertColumns(QtCore.QModelIndex(), c0, c0 + dc - 1)
            self.insertColumns(c0, dc, QtCore.QModelIndex())
            self.endInsertColumns()
        elif dc < 0:
            self.beginRemoveColumns(QtCore.QModelIndex(), c0 + dc, c0 - 1)
            self.removeColumns(c0 + dc, -dc, QtCore.QModelIndex())
            self.endRemoveColumns()

class DataFrameModel(AbstractDataFrameModel):
    
    @property
    def df(self) -> pd.DataFrame:
        return self._df
    
    @df.setter
    def df(self, data: pd.DataFrame):
        if data is self._df:
            return
        self.setShape(*data.shape)
        self._df = data
    
    def rowCount(self, parent=None):
        return self.df.shape[0]

    def columnCount(self, parent=None):
        return self.df.shape[1]
