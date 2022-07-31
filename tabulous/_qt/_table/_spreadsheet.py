from __future__ import annotations
from typing import TYPE_CHECKING, Any
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
        """Insert rows at the given row number and count."""
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
        """Insert columns at the given column number and count."""
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
        if count <= 0:
            return False
        df = self.df
        stop = row + count
        self.beginRemoveRows(parent, row, stop - 1)
        self.df = df.drop(index=df.index[row:count])
        self.endRemoveRows()
        return True

    def removeColumns(
        self, column: int, count: int, parent: QtCore.QModelIndex = None
    ) -> bool:
        if count <= 0:
            return False
        df = self.df
        stop = column + count
        self.beginRemoveColumns(parent, column, stop - 1)
        self.df = df.drop(columns=df.columns[column:stop])
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

    if TYPE_CHECKING:

        def model(self) -> SpreadSheetModel:
            ...

    def getDataFrame(self) -> pd.DataFrame:
        if self._data_cache is not None:
            return self._data_cache
        # Convert table data into a DataFrame with the optimal dtypes
        buf = StringIO(self._data_raw.to_csv(sep="\t", index_label="_INDEX_"))
        out = pd.read_csv(buf, sep="\t", index_col="_INDEX_")
        out.index.name = None
        self._data_cache = out
        return out

    def dataShape(self) -> tuple[int, int]:
        return self._data_raw.shape

    @QMutableSimpleTable._mgr.interface
    def setDataFrame(self, data: pd.DataFrame) -> None:
        """Set data frame as a string table."""
        self._data_raw = data.astype("string")
        self.model().setShape(data.index.size + 10, data.columns.size + 10)
        self._data_cache = None
        self.setFilter(None)
        self.refresh()
        return

    @setDataFrame.server
    def setDataFrame(self, data):
        return (getattr(self, "_data_raw", None),), {}

    def createModel(self) -> None:
        """Create spreadsheet model."""
        model = SpreadSheetModel(self)
        self._qtable_view.setModel(model)
        return None

    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value to the type of the table."""
        return value

    def readClipBoard(self):
        """Read clipboard as a string data frame."""
        return pd.read_clipboard(header=None, dtype="string")  # read as string

    def setDataFrameValue(self, r: int | slice, c: int | slice, value: Any) -> None:
        nr, nc = self._data_raw.shape
        rmax = _get_limit(r)
        cmax = _get_limit(c)
        need_expand = nr <= rmax or nc <= cmax

        if isinstance(value, str):
            if need_expand and value == "":
                # if user start editing a cell outside the data frame and did nothing,
                # do not expand the data frame.
                return
            if isinstance(r, int) and isinstance(c, int) and value == "NA":
                # if user start editing an empty cell and did nothing, do not set string "NA".
                index = self._qtable_view.model().index(r, c, QtCore.QModelIndex())
                text = self._qtable_view.model().data(
                    index, Qt.ItemDataRole.DisplayRole
                )
                if text == value:
                    return

        with self._mgr.merging(name="setDataFrameValue"):
            if need_expand:
                self.expandDataFrame(max(rmax - nr + 1, 0), max(cmax - nc + 1, 0))
            super().setDataFrameValue(r, c, value)
            self.setFilter(self._filter_slice)

        self._qtable_view.verticalHeader().resize(
            self._qtable_view.verticalHeader().sizeHint()
        )
        self._data_cache = None
        return None

    @QMutableSimpleTable._mgr.undoable
    def expandDataFrame(self, nrows: int, ncols: int):
        """Expand the data frame by adding empty rows and columns."""
        if not self.isEditable():
            return None
        self._data_raw = _pad_dataframe(self._data_raw, nrows, ncols)
        new_shape = self._data_raw.shape
        self.model().setShape(new_shape[0] + 10, new_shape[1] + 10)
        return None

    @expandDataFrame.undo_def
    def expandDataFrame(self, nrows: int, ncols: int):
        nr, nc = self._data_raw.shape
        self.model().removeRows(nr - nrows, nrows, QtCore.QModelIndex())
        self.model().removeColumns(nc - ncols, ncols, QtCore.QModelIndex())
        self._data_raw = self._data_raw.iloc[: nr - nrows, : nc - ncols]
        self.setFilter(self._filter_slice)
        self._data_cache = None
        return None

    def setVerticalHeaderValue(self, index: int, value: Any) -> None:
        """Set value of the table vertical header and DataFrame at the index."""
        nrows = self._data_raw.shape[0]
        if index >= nrows:
            if value == "":
                return
            self._data_raw = _pad_dataframe(self._data_raw, index - nrows + 1, 0)

        new_shape = self._data_raw.shape

        with self._mgr.blocked():
            self.setFilter(self._filter_slice)
        self.model().setShape(new_shape[0] + 10, new_shape[1] + 10)
        self._data_cache = None
        return super().setVerticalHeaderValue(index, value)

    def setHorizontalHeaderValue(self, index: int, value: Any) -> None:
        """Set value of the table horizontal header and DataFrame at the index."""
        ncols = self._data_raw.shape[1]
        if index >= ncols:
            if value == "":
                return
            self._data_raw = _pad_dataframe(self._data_raw, 0, index - ncols + 1)

        new_shape = self._data_raw.shape

        with self._mgr.blocked():
            self.setFilter(self._filter_slice)
        self.model().setShape(new_shape[0] + 10, new_shape[1] + 10)

        self._data_cache = None
        return super().setHorizontalHeaderValue(index, value)

    def showContextMenu(self, pos: QtCore.QPoint):
        menu = QtW.QMenu(self._qtable_view)
        index = self._qtable_view.indexAt(pos)
        row, col = index.row(), index.column()
        model = self.model()

        # fmt: off
        menu.addAction("Insert a row above", lambda: model.insertRows(row, 1, QtCore.QModelIndex()))
        menu.addAction("Insert a row below", lambda: model.insertRows(row + 1, 1, QtCore.QModelIndex()))
        menu.addAction("Insert a column on the left", lambda: model.insertColumns(col, 1, QtCore.QModelIndex()))
        menu.addAction("Insert a column on the right", lambda: model.insertColumns(col + 1, 1, QtCore.QModelIndex()))
        menu.addAction("Remove this row", lambda: model.removeRows(row, 1, QtCore.QModelIndex()))
        menu.addAction("Remove this column", lambda: model.removeColumns(col, 1, QtCore.QModelIndex()))
        # fmt: on

        return menu.exec(self._qtable_view.mapToGlobal(pos))


def _get_limit(a) -> int:
    if isinstance(a, int):
        amax = a
    elif isinstance(a, slice):
        amax = a.stop - 1
    else:
        raise TypeError(f"Cannot infer limit of type {type(a)}")
    return amax


def _pad_dataframe(df: pd.DataFrame, nr: int, nc: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            np.full((nr, nc), np.nan),
            index=range(nr),
            columns=range(nc),
            dtype="string",
        )

    # pad rows
    if nr > 0:
        if df.size == 0:
            df = pd.DataFrame(
                np.full((nr, 1), np.nan),
                index=range(nr),
                dtype="string",
            )
        else:
            _nr, _nc = df.shape
            ext = pd.DataFrame(
                np.full((nr, _nc), np.nan),
                index=range(_nr, _nr + nr),
                columns=df.columns,
                dtype="string",
            )
            df = pd.concat([df, ext], axis=0)

    # pad columns
    if nc > 0:
        if df.size == 0:
            df = pd.DataFrame(
                np.full((1, nc), np.nan),
                columns=range(nc),
                dtype="string",
            )
        else:
            _nr, _nc = df.shape
            ext = pd.DataFrame(
                np.full((_nr, nc), np.nan),
                index=df.index,
                columns=range(_nc, _nc + nc),
                dtype="string",
            )
            df = pd.concat([df, ext], axis=1)

    return df
