from __future__ import annotations
from typing import Any, Callable, Hashable
import warnings
from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt, Signal
import pandas as pd

from ....color import normalize_color, ColorType

# https://ymt-lab.com/post/2020/pyqt5-qtableview-pandas-qabstractitemmodel/


class AbstractDataFrameModel(QtCore.QAbstractTableModel):
    dataEdited = Signal(int, int, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df = pd.DataFrame([])

        self._editable = False
        self._foreground_colormap: dict[Hashable, Callable[[Any], ColorType]] = {}
        self._background_colormap: dict[Hashable, Callable[[Any], ColorType]] = {}

        self._data_role_map = {
            Qt.ItemDataRole.EditRole: self._data_display,
            Qt.ItemDataRole.DisplayRole: self._data_display,
            Qt.ItemDataRole.TextColorRole: self._data_text_color,
            Qt.ItemDataRole.ToolTipRole: self._data_tooltip,
            Qt.ItemDataRole.BackgroundColorRole: self._data_background_color,
        }

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def updateValue(self, r, c, val):
        # pandas warns but no problem
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._df.iloc[r, c] = val

    def data(
        self,
        index: QtCore.QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return QtCore.QVariant()
        if map := self._data_role_map.get(role, None):
            return map(index)
        return QtCore.QVariant()

    def _data_display(self, index: QtCore.QModelIndex):
        r, c = index.row(), index.column()
        if r < self.df.shape[0] and c < self.df.shape[1]:
            val = self.df.iat[r, c]
            if pd.isna(val):
                return "NA"
            return str(val)
        return QtCore.QVariant()

    def _data_text_color(self, index: QtCore.QModelIndex):
        r, c = index.row(), index.column()
        if r < self.df.shape[0] and c < self.df.shape[1]:
            colname = self.df.columns[c]
            val = self.df.iat[r, c]
            if mapper := self._foreground_colormap.get(colname, None):
                # If mapper is given for the column, call it.
                try:
                    col = mapper(val)
                    if col is None:
                        return QtCore.QVariant()
                    rgba = normalize_color(col)
                except Exception as e:
                    # since this method is called many times, errorous function should be
                    # deleted from the mapper.
                    self._foreground_colormap.pop(c)
                    raise e
                return QtGui.QColor(*rgba)
            if pd.isna(val):
                return QtGui.QColor(Qt.GlobalColor.gray)
        return QtCore.QVariant()

    def _data_tooltip(self, index: QtCore.QModelIndex):
        r, c = index.row(), index.column()
        if r < self.df.shape[0] and c < self.df.shape[1]:
            val = self.df.iat[r, c]
            dtype = self.df.dtypes.values[c]
            return f"{val!r} (dtype: {dtype})"
        return QtCore.QVariant()

    def _data_background_color(self, index: QtCore.QModelIndex):
        r, c = index.row(), index.column()
        if r < self.df.shape[0] and c < self.df.shape[1]:
            colname = self.df.columns[c]
            if mapper := self._background_colormap.get(colname, None):
                val = self.df.iat[r, c]
                try:
                    col = mapper(val)
                    if col is None:
                        return QtCore.QVariant()
                    rgba = normalize_color(col)
                except Exception as e:
                    # since this method is called many times, errorous function should be
                    # deleted from the mapper.
                    self._background_colormap.pop(c)
                    raise e
                return QtGui.QColor(*rgba)
        return QtCore.QVariant()

    def flags(self, index):
        _read_only = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if self._editable:
            return Qt.ItemFlag.ItemIsEditable | _read_only
        else:
            return _read_only

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                if section < self.df.columns.size:
                    return str(self.df.columns[section])
                return None
            elif role == Qt.ItemDataRole.ToolTipRole:
                if section < self.df.columns.size:
                    name = self.df.columns[section]
                    dtype = self.df.dtypes.values[section]
                    return f"{name} (dtype: {dtype})"
                return None

        if orientation == Qt.Orientation.Vertical:
            if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
                if section < self.df.index.size:
                    return str(self.df.index[section])
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
    """A concrete model for a pandas DataFrame."""

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
