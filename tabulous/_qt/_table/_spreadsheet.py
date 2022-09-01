from __future__ import annotations
from typing import TYPE_CHECKING, Any, Hashable
from io import StringIO
import numpy as np
import pandas as pd
from qtpy import QtCore
from qtpy.QtCore import Qt

from ._base import AbstractDataFrameModel, QMutableSimpleTable
from ._dtype import get_converter

_OUT_OF_BOUND_SIZE = 10  # 10 more rows and columns will be displayed.


class SpreadSheetModel(AbstractDataFrameModel):
    """A DataFrameModel for a spreadsheet."""

    @property
    def df(self) -> pd.DataFrame:  # NOTE: this returns a string data frame
        return self._df

    @df.setter
    def df(self, data: pd.DataFrame):
        self._df = data

    def rowCount(self, parent=None):
        from ..._global_variables import table

        return min(self._df.shape[0] + _OUT_OF_BOUND_SIZE, table.max_row_count)

    def columnCount(self, parent=None):
        from ..._global_variables import table

        return min(self._df.shape[1] + _OUT_OF_BOUND_SIZE, table.max_column_count)

    def _column_tooltip(self, section: int):
        name = self.df.columns[section]
        if dtype := self.parent()._columns_dtype.get(name, None):
            return f"{name} (dtype: {dtype})"
        else:
            dtype = self.df.dtypes.values[section]
            return f"{name} (dtype: infer)"

    def _data_tooltip(self, index: QtCore.QModelIndex):
        r, c = index.row(), index.column()
        if r < self.df.shape[0] and c < self.df.shape[1]:
            val = self.df.iat[r, c]
            name = self.df.columns[c]
            dtype = self.parent()._columns_dtype.get(name, None)
            if dtype is None:
                return f"{val!r} (dtype: infer)"
            else:
                return f"{val!r} (dtype: {dtype})"
        return QtCore.QVariant()

    # fmt: off
    if TYPE_CHECKING:
        def parent(self) -> QSpreadSheet: ...
    # fmt: on


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
        self._qtable_view.verticalHeader().setMinimumWidth(20)
        self._data_cache = None
        self._columns_dtype: dict[Hashable, np.dtype] = {}

    # fmt: off
    if TYPE_CHECKING:
        def model(self) -> SpreadSheetModel: ...
    # fmt: on

    def getDataFrame(self) -> pd.DataFrame:
        if self._data_cache is not None:
            return self._data_cache
        # Convert table data into a DataFrame with the optimal dtypes
        _sep = "\t"
        data_raw = self._data_raw
        if data_raw.shape[1] > 0:
            val = data_raw.to_csv(sep=_sep, index=False)
            buf = StringIO(val)
            out = pd.read_csv(
                buf,
                sep=_sep,
                header=0,
                names=data_raw.columns,
                dtype=self._columns_dtype,
            )
            out.index = data_raw.index
        else:
            out = pd.DataFrame(index=data_raw.index, columns=[])
        self._data_cache = out
        return out

    # def dataShown(self) -> pd.DataFrame:
    #     df = self.getDataFrame()
    #     return df.loc[list(self._filtered_index), list(self._filtered_columns)]

    def dataShape(self) -> tuple[int, int]:
        return self._data_raw.shape

    @QMutableSimpleTable._mgr.interface
    def setDataFrame(self, data: pd.DataFrame) -> None:
        """Set data frame as a string table."""
        self._data_raw = data.astype("string")
        self.model().setShape(
            data.index.size + _OUT_OF_BOUND_SIZE,
            data.columns.size + _OUT_OF_BOUND_SIZE,
        )
        self._data_cache = None
        self.setFilter(None)
        self.refreshTable()
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

        elif isinstance(value, pd.DataFrame) and any(value.dtypes != "string"):
            value = value.astype("string")

        with self._mgr.merging(formatter=lambda cmds: cmds[-2].format()):
            if need_expand:
                self.expandDataFrame(max(rmax - nr + 1, 0), max(cmax - nc + 1, 0))
                self._data_cache = None
            super().setDataFrameValue(r, c, value)
            self._data_cache = None
            self.setFilter(self._filter_slice)

        self._qtable_view.verticalHeader().resize(
            self._qtable_view.verticalHeader().sizeHint()
        )
        return None

    @QMutableSimpleTable._mgr.undoable
    def expandDataFrame(self, nrows: int, ncols: int):
        """Expand the data frame by adding empty rows and columns."""
        if not self.isEditable():
            return None
        self._data_raw = _pad_dataframe(self._data_raw, nrows, ncols)
        new_shape = self._data_raw.shape
        self.model().setShape(
            new_shape[0] + _OUT_OF_BOUND_SIZE,
            new_shape[1] + _OUT_OF_BOUND_SIZE,
        )
        return None

    @expandDataFrame.undo_def
    def expandDataFrame(self, nrows: int, ncols: int):
        nr, nc = self._data_raw.shape
        model = self.model()
        model.removeRows(nr - nrows, nrows, QtCore.QModelIndex())
        model.removeColumns(nc - ncols, ncols, QtCore.QModelIndex())
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
        self.setSelections([(slice(row, row + 1), slice(0, self._data_raw.shape[1]))])
        self._data_cache = None
        return None

    @_remove_rows.undo_def
    def _remove_rows(self, row: int, count: int, old_values: pd.DataFrame):
        self.insertRows(row, count)
        self.setDataFrameValue(
            r=slice(row, row + count),
            c=slice(0, old_values.columns.size),
            value=old_values,
        )
        self.setSelections([(slice(row, row + 1), slice(0, self._data_raw.shape[1]))])
        return None

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
        model = self.model()
        for index in range(column, column + count):
            colname = model.df.columns[index]
            model._background_colormap.pop(colname, None)
            model._foreground_colormap.pop(colname, None)

        self._data_raw = pd.concat(
            [self._data_raw.iloc[:, :column], self._data_raw.iloc[:, column + count :]],
            axis=1,
        )
        self.model().removeColumns(column, count, QtCore.QModelIndex())
        self.setFilter(self._filter_slice)
        self.setSelections(
            [(slice(0, self._data_raw.shape[0]), slice(column, column + 1))]
        )
        self._data_cache = None
        return None

    @_remove_columns.undo_def
    def _remove_columns(self, column: int, count: int, old_values: pd.DataFrame):
        self.insertColumns(column, count)
        self.setDataFrameValue(
            r=slice(0, old_values.index.size),
            c=slice(column, column + count),
            value=old_values,
        )
        self.setSelections(
            [(slice(0, self._data_raw.shape[0]), slice(column, column + 1))]
        )
        return None

    @_remove_columns.set_formatter
    def _remove_columns_fmt(self, column, count, old_values):
        s = "s" if count > 1 else ""
        return f"Remove {count} column{s} at columns={column}"

    def setVerticalHeaderValue(self, index: int, value: Any) -> None:
        """Set value of the table vertical header and DataFrame at the index."""
        if value == "":
            return
        nrows = self._data_raw.shape[0]

        with self._mgr.merging(formatter=lambda cmds: cmds[-1].format()):
            if index >= nrows:
                self.expandDataFrame(index - nrows + 1, 0)
            self.setFilter(self._filter_slice)
            super().setVerticalHeaderValue(index, value)
            self._data_cache = None

        return None

    def setHorizontalHeaderValue(self, index: int, value: Any) -> None:
        """Set value of the table horizontal header and DataFrame at the index."""
        if value == "":
            return
        ncols = self._data_raw.shape[1]

        with self._mgr.merging(formatter=lambda cmds: cmds[-1].format()):
            if index >= ncols:
                self.expandDataFrame(0, index - ncols + 1)
            colname = self._data_raw.columns[index]
            self.setFilter(self._filter_slice)
            super().setHorizontalHeaderValue(index, value)
            if colname in self._columns_dtype.keys():
                self.setColumnDtype(colname, self._columns_dtype[colname])
            self._data_cache = None

        return None

    @QMutableSimpleTable._mgr.interface
    def setColumnDtype(self, label: Hashable, dtype: Any | None) -> None:
        """Set the dtype of the column with the given label."""
        if dtype is None:
            self._columns_dtype.pop(label, None)
            return None
        if label not in self._data_raw.columns:
            raise KeyError(f"Column {label} not found.")
        from pandas.core.dtypes.common import pandas_dtype

        dtype = pandas_dtype(dtype)
        if self._columns_dtype.get(label, None) is not dtype:
            self._columns_dtype[label] = dtype
            self._data_cache = None
        return None

    @setColumnDtype.server
    def setColumnDtype(self, label: Hashable, dtype: Any):
        return (label, self._columns_dtype.get(label, None)), {}

    def _insert_row_above(self, row: int):
        return self.insertRows(row, 1)

    def _insert_row_below(self, row: int):
        return self.insertRows(row + 1, 1)

    def _insert_column_left(self, col: int):
        return self.insertColumns(col, 1)

    def _insert_column_right(self, col: int):
        return self.insertColumns(col + 1, 1)

    def _remove_this_row(self, row: int):
        return self.removeRows(row, 1)

    def _remove_this_column(self, col: int):
        return self.removeColumns(col, 1)

    def _set_column_dtype(self, col: int):
        from magicgui.widgets import Dialog

        # TODO: use a dialog to set the dtype

    def _install_actions(self):
        # fmt: off
        vheader = self._qtable_view.verticalHeader()
        vheader.registerAction("Insert row above")(self._insert_row_above)
        vheader.registerAction("Insert row below")(self._insert_row_below)
        vheader.registerAction("Remove this row")(self._remove_this_row)

        hheader = self._qtable_view.horizontalHeader()
        hheader.registerAction("Insert column left")(self._insert_column_left)
        hheader.registerAction("Insert column right")(self._insert_column_right)
        hheader.registerAction("Remove this column")(self._remove_this_column)
        hheader.registerAction("Set column dtype")(self._set_column_dtype)

        self.registerAction("Insert a row above")(lambda idx: self._insert_row_above(idx[0]))
        self.registerAction("Insert a row below")(lambda idx: self._insert_row_below(idx[0]))
        self.registerAction("Insert a column on the left")(lambda idx: self.insertColumns(idx[1]))
        self.registerAction("Insert a column on the right")(lambda idx: self.insertColumns(idx[1]))
        self.registerAction("Remove this row")(lambda idx: self._remove_this_row(idx[0]))
        self.registerAction("Remove this column")(lambda idx: self._remove_this_column(idx[1]))
        # fmt: on

        super()._install_actions()
        return None

    def _set_forground_colormap(self, index: int):
        return self._set_colormap(index, self.model()._foreground_colormap)

    def _set_background_colormap(self, index: int):
        return self._set_colormap(index, self.model()._background_colormap)

    def _set_colormap(self, index, colormap_dict: dict):
        from ._base._colormap import exec_colormap_dialog

        column_name = self._filtered_columns[index]
        df = self.getDataFrame()
        dtype: np.dtype = df.dtypes[column_name]
        _converter = get_converter(dtype.kind)
        if cmap := exec_colormap_dialog(df[column_name], self):

            def _cmap(val):
                try:
                    _val = _converter(val)
                except Exception:
                    return None
                else:
                    return cmap(_val)

            colormap_dict[column_name] = _cmap
            self.refresh()
        return None


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
    """A DataFrame filled with the given value."""
    return pd.DataFrame(
        np.full((nrows, ncols), value),
        index=index,
        columns=columns,
        dtype="string",
    )


def _pad_dataframe(df: pd.DataFrame, nr: int, nc: int, value: Any = "") -> pd.DataFrame:
    """Pad a dataframe by nr rows and nr columns with the given value."""
    if df.shape == (0, 0):
        return _df_full(nr, nc, value, index=range(nr), columns=range(nc))

    # pad rows
    _nr, _nc = df.shape
    if nr > 0:
        ext = _df_full(nr, _nc, value, index=range(_nr, _nr + nr), columns=df.columns)
        df = pd.concat([df, ext], axis=0)

    # pad columns
    _nr, _nc = df.shape  # NOTE: shape may have changed
    if nc > 0:
        ext = _df_full(_nr, nc, value, index=df.index, columns=range(_nc, _nc + nc))
        df = pd.concat([df, ext], axis=1)

    return df
