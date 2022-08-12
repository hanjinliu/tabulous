from __future__ import annotations
from typing import TYPE_CHECKING, Any
from io import StringIO
import numpy as np
import pandas as pd
from qtpy import QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt

from ._base import AbstractDataFrameModel, QMutableSimpleTable


class SpreadSheetModel(AbstractDataFrameModel):
    """A DataFrameModel for a spreadsheet."""

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @df.setter
    def df(self, data: pd.DataFrame):
        self._df = data

    def rowCount(self, parent=None):
        from ..._global_variables import table

        return min(self._df.shape[0] + 10, table.max_row_count)

    def columnCount(self, parent=None):
        from ..._global_variables import table

        return min(self._df.shape[1] + 10, table.max_column_count)

    # def insertRows(
    #     self, row: int, count: int, parent: QtCore.QModelIndex = None
    # ) -> bool:
    #     """Insert rows at the given row number and count."""
    #     df = self.df
    #     self.beginInsertRows(parent, row, row + count - 1)
    #     df0 = df.iloc[:row, :]
    #     df1 = pd.DataFrame(
    #         np.full((count, df.shape[1]), ""), columns=df.columns, dtype="string"
    #     )
    #     df2 = df.iloc[row:, :]
    #     self.df = pd.concat([df0, df1, df2], axis=0)
    #     self.endInsertRows()
    #     return True

    # def insertColumns(
    #     self, column: int, count: int, parent: QtCore.QModelIndex = None
    # ) -> bool:
    #     """Insert columns at the given column number and count."""
    #     df = self.df
    #     self.beginInsertColumns(parent, column, column + count - 1)
    #     df0 = df.iloc[:, :column]
    #     df1 = pd.DataFrame(
    #         np.full((df.shape[0], count), ""), index=df.index, dtype="string"
    #     )
    #     df2 = df.iloc[:, column:]
    #     self.df = pd.concat([df0, df1, df2], axis=1)
    #     self.endInsertColumns()
    #     return True

    # def removeRows(
    #     self, row: int, count: int, parent: QtCore.QModelIndex = None
    # ) -> bool:
    #     """Remove rows at the given column number and count."""
    #     if count <= 0:
    #         return False
    #     df = self.df
    #     stop = row + count
    #     self.beginRemoveRows(parent, row, stop - 1)
    #     self.df = df.drop(index=df.index[row:count])
    #     self.endRemoveRows()
    #     return True

    # def removeColumns(
    #     self, column: int, count: int, parent: QtCore.QModelIndex = None
    # ) -> bool:
    #     """Remove columns at the given column number and count."""
    #     if count <= 0:
    #         return False
    #     df = self.df
    #     stop = column + count
    #     self.beginRemoveColumns(parent, column, stop - 1)
    #     self.df = df.drop(columns=df.columns[column:stop])
    #     self.endRemoveColumns()
    #     return True


class QSpreadSheet(QMutableSimpleTable):
    """
    A table layer class that works similar to Excel sheet.

    Unlike ``QTableLayer``, this class does not have dtype. The dtype will be
    determined every time table data is converted into DataFrame. Table data
    is (almost) unbounded.
    """

    _DEFAULT_EDITABLE = True
    NaN = ""

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

    def updateValue(self, r, c, val):
        # NOTE: It seems very weird but the string array of pandas does not
        # support setting (N, 1) string array.
        if isinstance(val, pd.DataFrame) and isinstance(c, slice) and c.stop == 1:
            val = list(val.iloc[:, 0])

        return super().updateValue(r, c, val)

    @setDataFrame.server
    def setDataFrame(self, data):
        return (getattr(self, "_data_raw", None),), {}

    @setDataFrame.set_formatter
    def _setDataFrame_fmt(self, data: pd.DataFrame):
        return f"set new data of shape {data.shape}"

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
                model = self._qtable_view.model()
                index = model.index(r, c, QtCore.QModelIndex())
                text = model.data(index, Qt.ItemDataRole.DisplayRole)
                if text == value:
                    return

        with self._mgr.merging(formatter=lambda cmds: cmds[-2].format()):
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

    @QMutableSimpleTable._mgr.undoable
    def insertRows(self, row: int, count: int):
        """Insert rows at the given row number and count."""
        if self._filter_slice is not None:
            raise NotImplementedError("Cannot insert rows during filtering.")
        self._data_raw = pd.concat(
            [
                self._data_raw.iloc[:row, :],
                _df_full(
                    count, self._data_raw.shape[1], columns=self._data_raw.columns
                ),
                self._data_raw.iloc[row:, :],
            ],
            axis=0,
        )
        self.model().insertRows(row, count, QtCore.QModelIndex())
        self.setFilter(self._filter_slice)
        self._data_cache = None
        return None

    @insertRows.undo_def
    def insertRows(self, row: int, count: int):
        """Insert rows at the given row number and count."""
        return self.removeRows(row, count)

    @insertRows.set_formatter
    def _insertRows_fmt(self, row: int, count: int):
        s = "s" if count > 1 else ""
        return f"insert {count} row{s} at row={row}"

    @QMutableSimpleTable._mgr.undoable
    def insertColumns(self, column: int, count: int):
        """Insert columns at the given column number and count."""
        if self._filter_slice is not None:
            raise NotImplementedError("Cannot insert during filtering.")
        self._data_raw = pd.concat(
            [
                self._data_raw.iloc[:, :column],
                _df_full(self._data_raw.shape[0], count, index=self._data_raw.index),
                self._data_raw.iloc[:, column:],
            ],
            axis=1,
        )
        self.model().insertColumns(column, count, QtCore.QModelIndex())
        self.setFilter(self._filter_slice)
        self._data_cache = None
        return None

    @insertColumns.undo_def
    def insertColumns(self, column: int, count: int):
        """Insert columns at the given column number and count."""
        return self.removeColumns(column, count)

    @insertColumns.set_formatter
    def _insertColumns_fmt(self, column: int, count: int):
        s = "s" if count > 1 else ""
        return f"insert {count} column{s} at column={column}"

    def removeRows(self, row: int, count: int):
        """Remove rows at the given row number and count."""
        df = self.model().df.iloc[row : row + count, :]
        return self._remove_rows(row, count, df)

    @QMutableSimpleTable._mgr.undoable
    def _remove_rows(self, row: int, count: int, old_values: pd.DataFrame):
        self._data_raw = pd.concat(
            [self._data_raw.iloc[:row, :], self._data_raw.iloc[row + count :, :]],
            axis=0,
        )
        self.model().removeRows(row, count, QtCore.QModelIndex())
        self.setFilter(self._filter_slice)
        self._data_cache = None
        return None

    @_remove_rows.undo_def
    def _remove_rows(self, row: int, count: int, old_values: pd.DataFrame):
        self.insertRows(row, count)
        return self.setDataFrameValue(
            r=slice(row, row + count),
            c=slice(0, old_values.columns.size),
            value=old_values,
        )

    @_remove_rows.set_formatter
    def _remove_rows_fmt(self, row, count, old_values):
        s = "s" if count > 1 else ""
        return f"Remove {count} row{s} at row={row}"

    def removeColumns(self, column: int, count: int):
        """Remove columns at the given column number and count."""
        df = self.model().df.iloc[:, column : column + count]
        return self._remove_columns(column, count, df)

    @QMutableSimpleTable._mgr.undoable
    def _remove_columns(self, column: int, count: int, old_values: pd.DataFrame):
        self._data_raw = pd.concat(
            [self._data_raw.iloc[:, :column], self._data_raw.iloc[:, column + count :]],
            axis=1,
        )
        self.model().removeColumns(column, count, QtCore.QModelIndex())
        self.setFilter(self._filter_slice)
        self._data_cache = None
        return None

    @_remove_columns.undo_def
    def _remove_columns(self, column: int, count: int, old_values: pd.DataFrame):
        self.insertColumns(column, count)
        return self.setDataFrameValue(
            r=slice(0, old_values.index.size),
            c=slice(column, column + count),
            value=old_values,
        )

    @_remove_columns.set_formatter
    def _remove_columns_fmt(self, column, count, old_values):
        s = "s" if count > 1 else ""
        return f"Remove {count} column{s} at columns={column}"

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

        # fmt: off
        menu.addAction("Insert a row above", lambda: self.insertRows(row, 1))
        menu.addAction("Insert a row below", lambda: self.insertRows(row + 1, 1))
        menu.addAction("Insert a column on the left", lambda: self.insertColumns(col, 1))
        menu.addAction("Insert a column on the right", lambda: self.insertColumns(col + 1, 1))
        menu.addAction("Remove this row", lambda: self.removeRows(row, 1))
        menu.addAction("Remove this column", lambda: self.removeColumns(col, 1))
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


def _df_full(
    nrows: int, ncols: int, value="", index=None, columns=None
) -> pd.DataFrame:
    return pd.DataFrame(
        np.full((nrows, ncols), value),
        index=index,
        columns=columns,
        dtype="string",
    )


def _pad_dataframe(df: pd.DataFrame, nr: int, nc: int, value="") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            np.full((nr, nc), value),
            index=range(nr),
            columns=range(nc),
            dtype="string",
        )

    # pad rows
    if nr > 0:
        if df.size == 0:
            df = pd.DataFrame(
                np.full((nr, 1), value),
                index=range(nr),
                dtype="string",
            )
        else:
            _nr, _nc = df.shape
            ext = pd.DataFrame(
                np.full((nr, _nc), value),
                index=range(_nr, _nr + nr),
                columns=df.columns,
                dtype="string",
            )
            df = pd.concat([df, ext], axis=0)

    # pad columns
    if nc > 0:
        if df.size == 0:
            df = pd.DataFrame(
                np.full((1, nc), value),
                columns=range(nc),
                dtype="string",
            )
        else:
            _nr, _nc = df.shape
            ext = pd.DataFrame(
                np.full((_nr, nc), value),
                index=df.index,
                columns=range(_nc, _nc + nc),
                dtype="string",
            )
            df = pd.concat([df, ext], axis=1)

    return df
