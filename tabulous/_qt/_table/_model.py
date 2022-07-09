from __future__ import annotations
from typing import TYPE_CHECKING
import weakref
from qtpy import QtCore
from qtpy.QtCore import Qt
import pandas as pd

# https://ymt-lab.com/post/2020/pyqt5-qtableview-pandas-qabstractitemmodel/

class AbstractDataFrameModel(QtCore.QAbstractItemModel):
    def __init__(self, parent=None, data: pd.DataFrame=None):
        super().__init__(parent)
        self.df = data
    
    @property
    def df(self) -> pd.DataFrame:
        df = self._data_ref()
        if df is None:
            raise ValueError("DataFrame has been deleted.")
        return df
    
    @df.setter
    def df(self, data: pd.DataFrame):
        self._data_ref = weakref.ref(data)

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

    # def flags(self, index):
    #     return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.df.columns[section]
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return self.df.index[section]

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        return self.createIndex(row, column, QtCore.QModelIndex())

    # def insertColumns(self, column, count, parent=QtCore.QModelIndex()):
    #     self.beginInsertColumns(parent, column, column + count - 1)
    #     columns = [str(self.columnCount()+i+1) for i in range(count)]
    #     left = self.df.iloc[:, 0:column]
    #     mid = pd.DataFrame(index=self.df.index, columns=columns)
    #     right = self.df.iloc[:, column + count - 1: self.columnCount()]
    #     self.df = pd.concat([left, mid, right], axis=1)
        
    #     self.endInsertColumns()

    # def insertRows(self, row, count, parent=QtCore.QModelIndex()):
    #     self.beginInsertRows(parent, row, row + count - 1)
    #     indices = [str(self.rowCount() + i) for i in range(count)]
    #     left = self.df[0:row]
    #     mid = pd.DataFrame(index=indices, columns=self.df.columns)
    #     right = self.df[row+count-1:self.rowCount()]
    #     self.df = pd.concat([left, mid, right])
    #     self.endInsertRows()

    # def removeColumns(self, column, count, parent=QtCore.QModelIndex()):
    #     self.beginRemoveColumns(parent, column, column + count - 1)
    #     left = self.df.iloc[:, 0:column]
    #     right = self.df.iloc[:, column+count:self.columnCount()]
    #     self.df = pd.concat([left, right], axis=1)
    #     self.endRemoveColumns()

    # def removeRows(self, row, count, parent=QtCore.QModelIndex()):
    #     self.beginRemoveRows(parent, row, row + count - 1)
        
    #     left = self.df.iloc[0:row]
    #     right = self.df.iloc[row+count:self.rowCount()]
    #     self.df = pd.concat([left, right], axis=0)
    #     self.endRemoveRows()
        

    # def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
    #     if role == Qt.ItemDataRole.EditRole:
    #         self.df.iat[index.row(), index.column()] = value
    #         return True
    #     return False