from __future__ import annotations
from typing import Any
from io import StringIO
import numpy as np
import pandas as pd
from qtpy import QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt

from ._base import AbstractDataFrameModel, QMutableSimpleTable

MAX_ROW_SIZE = 100000
MAX_COLUMN_SIZE = 100000


class SpreadSheetModel(AbstractDataFrameModel):
    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @df.setter
    def df(self, data: pd.DataFrame):
        self._df = data

    def rowCount(self, parent=None):
        return min(self._df.shape[0] + 10, MAX_ROW_SIZE)

    def columnCount(self, parent=None):
        return min(self._df.shape[1] + 10, MAX_COLUMN_SIZE)

    def insertRows(
        self, row: int, count: int, parent: QtCore.QModelIndex = None
    ) -> bool:
        df = self.df
        self.beginInsertRows(parent, row, row + count - 1)
        df0 = df.iloc[:row, :]
        df1 = pd.DataFrame(
            np.full((count, df.shape[1]), np.nan), columns=df.columns, dtype="string"
        )
        df2 = df.iloc[row:, :]
        self.df = pd.concat([df0, df1, df2], axis=0)
        self.endInsertRows()
        return True

    def insertColumns(
        self, column: int, count: int, parent: QtCore.QModelIndex = None
    ) -> bool:
        df = self.df
        self.beginInsertColumns(parent, column, column + count - 1)
        df0 = df.iloc[:, :column]
        df1 = pd.DataFrame(
            np.full((df.shape[0], count), np.nan), index=df.index, dtype="string"
        )
        df2 = df.iloc[:, column:]
        self.df = pd.concat([df0, df1, df2], axis=1)
        self.endInsertColumns()
        return True

    def removeRows(
        self, row: int, count: int, parent: QtCore.QModelIndex = None
    ) -> bool:
        df = self.df
        self.beginRemoveRows(parent, row, row + count - 1)
        self.df = df.drop(index=df.index[row])
        self.endRemoveRows()
        return True

    def removeColumns(
        self, column: int, count: int, parent: QtCore.QModelIndex = None
    ) -> bool:
        df = self.df
        self.beginRemoveColumns(parent, column, column + count - 1)
        self.df = df.drop(columns=df.columns[column])
        self.endRemoveColumns()
        return True


class QSpreadSheet(QMutableSimpleTable):
    """
    A table layer class that works similar to Excel sheet.

    Unlike ``QTableLayer``, this class does not have dtype. The dtype will be
    determined every time table data is converted into DataFrame. Table data
    is (almost) unbounded.
    """

    _DEFAULT_EDITABLE = True

    def __init__(self, parent=None, data: pd.DataFrame | None = None):
        super().__init__(parent, data)
        self._data_cache = None
        self._qtable_view.rightClickedSignal.connect(self.showContextMenu)

    def getDataFrame(self) -> pd.DataFrame:
        if self._data_cache is not None:
            return self._data_cache
        # Convert table data into a DataFrame with the optimal dtypes
        buf = StringIO(self._data_raw.to_csv(sep="\t", index_label="_INDEX_"))
        out = pd.read_csv(buf, sep="\t", index_col="_INDEX_")
        out.index.name = None
        self._data_cache = out
        return out

    def setDataFrame(self, data: pd.DataFrame) -> None:
        self._data_raw = data.astype("string")
        self.model().setShape(data.index.size + 10, data.columns.size + 10)
        self._data_cache = None
        self.setFilter(None)
        self.refresh()
        return

    def createModel(self) -> None:
        """Create spreadsheet model."""
        model = SpreadSheetModel(self)
        self._qtable_view.setModel(model)
        return None

    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value to the type of the table."""
        return value

    def readClipBoard(self):
        return pd.read_clipboard(header=None).astype("string")

    def setDataFrameValue(self, r: int | slice, c: int | slice, value: Any) -> None:
        nr, nc = self._data_raw.shape
        rmax = _get_limit(r)
        cmax = _get_limit(c)
        if nr <= rmax or nc <= cmax:
            if nr <= rmax:
                self.expandRows(rmax - nr + 1)
            if self._data_raw.shape[1] <= cmax:  # NOTE: DataFrame shape is updated
                self.expandColumns(cmax - nc + 1)
            new_shape = self._data_raw.shape
            self.model().setShape(new_shape[0] + 10, new_shape[1] + 10)

        self._data_cache = None
        super().setDataFrameValue(r, c, value)

        self.setFilter(self._filter_slice)
        self._qtable_view.verticalHeader().resize(
            self._qtable_view.verticalHeader().sizeHint()
        )
        return None

    def expandRows(self, n_expand: int):
        if self._data_raw.size == 0:
            self._data_raw = pd.DataFrame(
                np.full((n_expand, 1), np.nan),
                index=range(n_expand),
                dtype="string",
            )
            return
        nr, nc = self._data_raw.shape
        ext = pd.DataFrame(
            np.full((n_expand, nc), np.nan),
            index=range(nr, n_expand + nr),
            columns=self._data_raw.columns,
            dtype="string",
        )
        self._data_raw = pd.concat([self._data_raw, ext], axis=0)
        return None

    def expandColumns(self, n_expand: int):
        if self._data_raw.size == 0:
            self._data_raw = pd.DataFrame(
                np.full((1, n_expand), np.nan),
                columns=range(n_expand),
                dtype="string",
            )
            return
        nr, nc = self._data_raw.shape
        ext = pd.DataFrame(
            np.full((nr, n_expand), np.nan),
            index=self._data_raw.index,
            columns=range(nc, n_expand + nc),
            dtype="string",
        )
        self._data_raw = pd.concat([self._data_raw, ext], axis=1)
        return None

    def setVerticalHeaderValue(self, index: int, value: Any) -> None:
        """Set value of the table vertical header and DataFrame at the index."""
        nrows = self._data_raw.shape[0]
        if index >= nrows:
            if value == "":
                return
            self.expandRows(index - nrows + 1)
            self.setFilter(self._filter_slice)

        new_shape = self._data_raw.shape
        self._data_cache = None
        self.setFilter(self._filter_slice)
        self.model().setShape(new_shape[0] + 10, new_shape[1] + 10)

        return super().setVerticalHeaderValue(index, value)

    def setHorizontalHeaderValue(self, index: int, value: Any) -> None:
        """Set value of the table horizontal header and DataFrame at the index."""
        ncols = self._data_raw.shape[1]
        if index >= ncols:
            if value == "":
                return
            self.expandColumns(index - ncols + 1)
            self.setFilter(self._filter_slice)

        new_shape = self._data_raw.shape
        self._data_cache = None
        self.setFilter(self._filter_slice)
        self.model().setShape(new_shape[0] + 10, new_shape[1] + 10)

        return super().setHorizontalHeaderValue(index, value)

    def showContextMenu(self, pos: QtCore.QPoint):
        menu = QtW.QMenu(self._qtable_view)
        index = self._qtable_view.indexAt(pos)
        row, col = index.row(), index.column()
        model = self.model()
        menu.addAction(
            "Insert a row above", lambda: model.insertRows(row, 1, QtCore.QModelIndex())
        )
        menu.addAction(
            "Insert a row below",
            lambda: model.insertRows(row + 1, 1, QtCore.QModelIndex()),
        )
        menu.addAction(
            "Insert a column on the left",
            lambda: model.insertColumns(col, 1, QtCore.QModelIndex()),
        )
        menu.addAction(
            "Insert a column on the right",
            lambda: model.insertColumns(col + 1, 1, QtCore.QModelIndex()),
        )
        menu.addAction(
            "Remove this row", lambda: model.removeRows(row, 1, QtCore.QModelIndex())
        )
        menu.addAction(
            "Remove this column",
            lambda: model.removeColumns(col, 1, QtCore.QModelIndex()),
        )
        return menu.exec(self._qtable_view.mapToGlobal(pos))


def _get_limit(a) -> int:
    if isinstance(a, int):
        amax = a
    elif isinstance(a, slice):
        amax = a.stop - 1
    else:
        raise TypeError(f"Cannot infer limit of type {type(a)}")
    return amax
