from __future__ import annotations

from typing import TYPE_CHECKING, Any, Hashable
import re
from functools import cached_property
from io import StringIO

import numpy as np
import pandas as pd
from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt

from magicgui import widgets as mWdg
from collections_undo import arguments

from tabulous.commands.selection import add_float_slider


from ._base import AbstractDataFrameModel, QMutableSimpleTable
from tabulous._dtype import get_converter, get_dtype, DTypeMap, DefaultValidator
from tabulous.color import normalize_color
from tabulous.types import ItemInfo
from tabulous import commands as cmds
from tabulous._text_formatter import DefaultFormatter

if TYPE_CHECKING:
    from magicgui.widgets._bases import ValueWidget

# More rows/columns will be displayed
_OUT_OF_BOUND_R = 60
_OUT_OF_BOUND_C = 10
_STRING_DTYPE = get_dtype("string")
_EMPTY = object()
_EXP_FLOAT = re.compile(r"[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)")


class SpreadSheetModel(AbstractDataFrameModel):
    """A DataFrameModel for a spreadsheet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from tabulous._utils import get_config

        self._table_config = get_config().table
        self._columns_dtype = self.parent()._columns_dtype

    @cached_property
    def _out_of_bound_color(self) -> QtGui.QColor:
        if self.parent()._qtable_view.parentViewer()._white_background:
            return QtGui.QColor(248, 248, 255)
        else:
            return QtGui.QColor(7, 7, 0)

    @property
    def df(self) -> pd.DataFrame:  # NOTE: this returns a string data frame
        return self._df

    @df.setter
    def df(self, data: pd.DataFrame):
        self._df = data

    def rowCount(self, parent=None):
        return min(
            self._df.shape[0] + _OUT_OF_BOUND_R,
            self._table_config.max_row_count,
        )

    def columnCount(self, parent=None):
        return min(
            self._df.shape[1] + _OUT_OF_BOUND_C,
            self._table_config.max_column_count,
        )

    def _data_display(self, index: QtCore.QModelIndex):
        """Display role."""
        r, c = index.row(), index.column()
        df = self.df
        if r < df.shape[0] and c < df.shape[1]:
            val = df.iat[r, c]
            colname = df.columns[c]
            if mapper := self._text_formatter.get(colname, None):
                _converter = get_converter(
                    self._columns_dtype.get(colname, _STRING_DTYPE).kind
                )
                try:
                    text = str(mapper(_converter(val)))
                except Exception:
                    text = self._FORMAT_ERROR
            else:
                text = str(val)
            # Exponentially formatted float numbers are not displayed correctly.
            if _EXP_FLOAT.match(text):
                text = format(float(text), ".5e")
            return text
        return QtCore.QVariant()

    def _data_background_color(self, index: QtCore.QModelIndex):
        r, c = index.row(), index.column()
        df = self.df
        if r < df.shape[0] and c < df.shape[1]:
            colname = df.columns[c]
            if mapper := self._background_colormap.get(colname, None):
                val = df.iat[r, c]
                try:
                    col = mapper(val)
                    if col is None:
                        return QtCore.QVariant()
                    rgba = normalize_color(col)
                except Exception as e:
                    # since this method is called many times, errorous function should be
                    # deleted from the mapper.
                    self._background_colormap.pop(colname)
                    raise e
                return QtGui.QColor(*rgba)
        else:
            return self._out_of_bound_color  # add shade to the out-of-range cells

    def _column_tooltip(self, section: int):
        name = self.df.columns[section]
        if dtype := self._columns_dtype.get(name, None):
            return f"{name} (dtype: {dtype})"
        else:
            dtype = self.df.dtypes.values[section]
            return f"{name} (dtype: infer)"

    def _data_tooltip(self, index: QtCore.QModelIndex):
        r, c = index.row(), index.column()
        if r < self.df.shape[0] and c < self.df.shape[1]:
            val = self.df.iat[r, c]
            name = self.df.columns[c]
            if ref_expr := self.parent()._get_ref_expr(r, c):
                ref = f"\nExpr: {ref_expr}"
            if slot := self.parent()._qtable_view._table_map.get((r, c), None):
                ref = f"\nExpr: {slot.as_literal()}"
                if slot._current_error is not None:
                    ref += "\n" + slot.format_error()
            else:
                ref = ""
            dtype = self._columns_dtype.get(name, None)
            if dtype is None:
                return f"{val!r} (dtype: infer){ref}"
            else:
                return f"{val!r} (dtype: {dtype}){ref}"
        return QtCore.QVariant()

    if TYPE_CHECKING:

        def parent(self) -> QSpreadSheet:
            ...


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
        self._columns_dtype = DTypeMap()
        super().__init__(parent, data)
        self._qtable_view.verticalHeader().setMinimumWidth(20)

    if TYPE_CHECKING:

        def model(self) -> SpreadSheetModel:
            ...

    def getDataFrame(self) -> pd.DataFrame:
        if self._data_cache is not None:
            return self._data_cache
        # Convert table data into a DataFrame with the optimal dtypes
        _sep = "\t"
        data_raw = self._data_raw
        if data_raw.shape[1] > 0:
            val = data_raw.to_csv(sep=_sep, index=False)
            buf = StringIO(val)
            out: pd.DataFrame = pd.read_csv(
                buf,
                sep=_sep,
                header=0,
                na_values=["#ERROR"],
                names=data_raw.columns,
                **self._columns_dtype.as_pandas_kwargs(),
            )
            out.index = data_raw.index
        else:
            out = pd.DataFrame(index=data_raw.index, columns=[])
        self._data_cache = out
        return out

    def dataShape(self) -> tuple[int, int]:
        """Shape of data."""
        return self._data_raw.shape

    def dataShown(self, parse: bool = False) -> pd.DataFrame:
        """Return the shown dataframe (consider filter)."""
        if parse:
            df = self.getDataFrame()
            if self._filter_slice is not None:
                if callable(self._filter_slice):
                    sl = self._filter_slice(df)
                else:
                    sl = self._filter_slice
                return df[sl]
            return df
        else:
            return self.model().df

    @QMutableSimpleTable._mgr.interface
    def setDataFrame(self, data: pd.DataFrame) -> None:
        """Set data frame as a string table."""
        self._data_raw = data.astype(_STRING_DTYPE)
        self.model().setShape(
            data.index.size + _OUT_OF_BOUND_R,
            data.columns.size + _OUT_OF_BOUND_C,
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
        return arguments(getattr(self, "_data_raw", None))

    @setDataFrame.set_formatter
    def _setDataFrame_fmt(self, data: pd.DataFrame):
        return f"set new data of shape {data.shape}"

    __delete = object()

    @QMutableSimpleTable._mgr.interface
    def assignColumns(self, serieses: dict[str, pd.Series]):
        to_delete = set()
        to_assign: dict[str, pd.Series] = {}
        for k, v in serieses.items():
            if v is self.__delete:
                to_delete.add(k)
            else:
                to_assign[k] = v
        self._data_raw: pd.DataFrame = self._data_raw.assign(**to_assign).drop(
            to_delete, axis=1
        )
        nr, nc = self._data_raw.shape
        self.model().df = self._data_raw
        self.model().setShape(
            nr + _OUT_OF_BOUND_R,
            nc + _OUT_OF_BOUND_C,
        )
        self.setFilter(None)
        self.refreshTable()
        self._data_cache = None
        return None

    @assignColumns.server
    def assignColumns(self, serieses: dict[str, pd.Series]):
        columns = self._data_raw.columns
        old_param: dict[str, pd.Series] = {}
        for k in serieses.keys():
            if k in columns:
                old_param[k] = self._data_raw[k]
            else:
                old_param[k] = self.__delete
        return arguments(old_param)

    @assignColumns.set_formatter
    def _assignColumns_fmt(self, serieses: dict[str, pd.Series]):
        keys = set(serieses.keys())
        return f"assign new data to {keys}"

    def createModel(self) -> None:
        """Create spreadsheet model."""
        model = SpreadSheetModel(self)
        self._qtable_view.setModel(model)
        return None

    def convertValue(self, c: int, value: Any) -> Any:
        """Convert value to the type of the table."""
        return value

    def readClipBoard(self, sep=r"\s+"):
        """Read clipboard as a string data frame."""
        return pd.read_clipboard(
            header=None, sep=sep, dtype=_STRING_DTYPE
        )  # read as string

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
            value = value.astype(_STRING_DTYPE)

        with self._mgr.merging(formatter=lambda cmds: cmds[-2].format()):
            if need_expand:
                self.expandDataFrame(max(rmax - nr + 1, 0), max(cmax - nc + 1, 0))
            super().setDataFrameValue(r, c, value)
            self.setFilter(self._filter_slice)

        self._qtable_view.verticalHeader().resize(
            self._qtable_view.verticalHeader().sizeHint()
        )
        return None

    def setLabeledData(self, r: slice, c: slice, value: pd.Series):
        nr, nc = self._data_raw.shape
        rmax = _get_limit(r)
        cmax = _get_limit(c)
        need_expand = nr <= rmax or nc <= cmax

        if value.dtype != "string":
            value = value.astype(_STRING_DTYPE)

        with self._mgr.merging(formatter=lambda cmds: cmds[-2].format()):
            if need_expand:
                self.expandDataFrame(max(rmax - nr + 1, 0), max(cmax - nc + 1, 0))
            super().setLabeledData(r, c, value)
            self.setFilter(self._filter_slice)

        self._qtable_view.verticalHeader().resize(
            self._qtable_view.verticalHeader().sizeHint()
        )
        return None

    def _pre_set_array(self, r: slice, c: slice, _value: pd.DataFrame):
        """Convert input dataframe for setting to data[r, c]."""
        if len(self.model()._validator) == 0:
            # use faster method if no validator is set
            out = self._data_raw.iloc[r, c].copy()
            if _value.size == 1:
                out[:] = str(_value.values[0, 0])
            else:
                # NOTE: It seems weird but setitem of pandas string array fails in
                # certain cases that the value is of shape (N, 1).
                try:
                    out[:] = _value.astype(_STRING_DTYPE).values
                except Exception:
                    out.values[:] = _value.astype(_STRING_DTYPE).values
            return out
        return super()._pre_set_array(r, c, _value)

    @QMutableSimpleTable._mgr.undoable
    def expandDataFrame(self, nrows: int, ncols: int):
        """Expand the data frame by adding empty rows and columns."""
        if not self.isEditable():
            return None
        self._data_raw = _pad_dataframe(self._data_raw, nrows, ncols)
        new_shape = self._data_raw.shape
        self.model().setShape(
            new_shape[0] + _OUT_OF_BOUND_R,
            new_shape[1] + _OUT_OF_BOUND_C,
        )
        return None

    @expandDataFrame.undo_def
    def expandDataFrame(self, nrows: int, ncols: int):
        nr, nc = self._data_raw.shape
        model = self.model()
        self._data_raw = self._data_raw.iloc[: nr - nrows, : nc - ncols]
        model.setShape(
            self._data_raw.shape[0] + _OUT_OF_BOUND_R,
            self._data_raw.shape[1] + _OUT_OF_BOUND_C,
        )
        self.setFilter(self._filter_slice)
        self._data_cache = None
        return None

    @QMutableSimpleTable._mgr.undoable
    def insertRows(self, row: int, count: int, value: Any = _EMPTY):
        """Insert rows at the given row number and count."""
        if self._filter_slice is not None:
            raise NotImplementedError("Cannot insert rows during filtering.")

        index_existing = self._data_raw.index

        if value is _EMPTY:
            # determine index labels
            index: list[int] = []
            i = 0
            while True:
                if i not in index_existing:
                    index.append(i)
                    if len(index) >= count:
                        break
                else:
                    i += 1

            value = _df_full(
                nrows=count,
                ncols=self._data_raw.shape[1],
                index=index,
                columns=self._data_raw.columns,
            )

        self._data_raw = pd.concat(
            [
                self._data_raw.iloc[:row, :],
                value,
                self._data_raw.iloc[row:, :],
            ],
            axis=0,
        )
        if isinstance(index_existing, pd.RangeIndex):
            self._data_raw.index = pd.RangeIndex(0, self._data_raw.index.size)
        self.model().insertRows(row, count, QtCore.QModelIndex())
        self.setFilter(self._filter_slice)
        self._data_cache = None

        # update indices
        self._qtable_view._table_map.insert_rows(row, count)
        self._qtable_view._selection_model.insert_rows(row, count)
        self._qtable_view._highlight_model.insert_rows(row, count)

        info = ItemInfo(
            slice(row, row + count),
            slice(None),
            value,
            ItemInfo.INSERTED,
        )
        self.itemChangedSignal.emit(info)
        return None

    @insertRows.undo_def
    def insertRows(self, row: int, count: int, value: Any = _EMPTY):
        """Insert rows at the given row number and count."""
        return self.removeRows(row, count)

    @insertRows.set_formatter
    def _insertRows_fmt(self, row: int, count: int, value: Any = _EMPTY):
        s = "s" if count > 1 else ""
        return f"insert {count} row{s} at row={row}"

    @QMutableSimpleTable._mgr.undoable
    def insertColumns(self, col: int, count: int, value: Any = _EMPTY):
        """Insert columns at the given column number and count."""
        if self._filter_slice is not None:
            raise NotImplementedError("Cannot insert during filtering.")

        columns_existing = self._data_raw.columns

        if value is _EMPTY:
            # determine column labels
            columns: list[int] = []
            i = 0
            while True:
                if i not in columns_existing:
                    columns.append(i)
                    if len(columns) >= count:
                        break
                else:
                    i += 1

            value = _df_full(
                nrows=self._data_raw.shape[0],
                ncols=count,
                index=self._data_raw.index,
                columns=columns,
            )

        self._data_raw = pd.concat(
            [
                self._data_raw.iloc[:, :col],
                value,
                self._data_raw.iloc[:, col:],
            ],
            axis=1,
        )
        if isinstance(columns_existing, pd.RangeIndex):
            self._data_raw.columns = pd.RangeIndex(0, self._data_raw.columns.size)
        self.model().insertColumns(col, count, QtCore.QModelIndex())
        self.setFilter(self._filter_slice)
        self._data_cache = None

        # update indices
        self._qtable_view._table_map.insert_columns(col, count)
        self._qtable_view._selection_model.insert_columns(col, count)
        self._qtable_view._highlight_model.insert_columns(col, count)

        info = ItemInfo(
            slice(None),
            slice(col, col + count),
            value,
            ItemInfo.INSERTED,
        )
        self.itemChangedSignal.emit(info)
        return None

    @insertColumns.undo_def
    def insertColumns(self, col: int, count: int, value: Any = _EMPTY):
        """Insert columns at the given column number and count."""
        return self.removeColumns(col, count)

    @insertColumns.set_formatter
    def _insertColumns_fmt(self, col: int, count: int, value: Any = _EMPTY):
        s = "s" if count > 1 else ""
        return f"insert {count} column{s} at column={col}"

    def removeRows(self, row: int, count: int):
        """Remove rows at the given row number and count."""
        df = self.model().df.iloc[row : row + count, :]

        with self._mgr.merging():
            self._clear_incell_slots(
                slice(row, row + count),
                slice(0, self._data_raw.shape[1]),
            )
            self._remove_rows(row, count, df)
        return None

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

        self._qtable_view._table_map.remove_rows(row, count)
        self._qtable_view._highlight_model.remove_rows(row, count)
        self._qtable_view._selection_model.remove_rows(row, count)
        info = ItemInfo(
            slice(row, row + count), slice(None), ItemInfo.DELETED, old_values
        )
        self.itemChangedSignal.emit(info)
        return None

    @_remove_rows.undo_def
    def _remove_rows(self, row: int, count: int, old_values: pd.DataFrame):
        self.insertRows(row, count, old_values)
        self.setSelections([(slice(row, row + 1), slice(0, self._data_raw.shape[1]))])
        return None

    @_remove_rows.set_formatter
    def _remove_rows_fmt(self, row, count, old_values):
        s = "s" if count > 1 else ""
        if count == 1:
            sl = row
        else:
            sl = f"{row}:{row + count}"
        return f"Remove row{s} at position {sl}"

    def removeColumns(self, column: int, count: int):
        """Remove columns at the given column number and count."""
        df = self.model().df.iloc[:, column : column + count]
        with self._mgr.merging():
            self._clear_incell_slots(
                slice(0, self._data_raw.shape[0]),
                slice(column, column + count),
            )
            self._remove_columns(column, count, df)
        return None

    @QMutableSimpleTable._mgr.undoable
    def _remove_columns(self, col: int, count: int, old_values: pd.DataFrame):
        model = self.model()
        for index in range(col, col + count):
            colname = model.df.columns[index]
            model.delete_column(colname)
            self._columns_dtype.pop(colname, None)

        self._data_raw = pd.concat(
            [self._data_raw.iloc[:, :col], self._data_raw.iloc[:, col + count :]],
            axis=1,
        )
        self.model().removeColumns(col, count, QtCore.QModelIndex())
        self.setFilter(self._filter_slice)
        self.setSelections([(slice(0, self._data_raw.shape[0]), slice(col, col + 1))])
        self._data_cache = None

        self._qtable_view._table_map.remove_columns(col, count)
        self._qtable_view._highlight_model.remove_columns(col, count)
        self._qtable_view._selection_model.remove_columns(col, count)
        info = ItemInfo(
            slice(None), slice(col, col + count), ItemInfo.DELETED, old_values
        )
        self.itemChangedSignal.emit(info)
        return None

    @_remove_columns.undo_def
    def _remove_columns(self, col: int, count: int, old_values: pd.DataFrame):
        self.insertColumns(col, count, old_values)
        self.setSelections([(slice(0, self._data_raw.shape[0]), slice(col, col + 1))])
        return None

    @_remove_columns.set_formatter
    def _remove_columns_fmt(self, col, count, old_values):
        s = "s" if count > 1 else ""
        if count == 1:
            sl = col
        else:
            sl = f"{col}:{col + count}"
        return f"Remove column{s} at position {sl}"

    @QMutableSimpleTable._mgr.interface
    def _set_widget_at_index(self, r: int, c: int, widget: ValueWidget | None) -> None:
        index = self.model().index(r, c)
        if wdt := self._qtable_view.indexWidget(index):
            try:
                self.itemChangedSignal.disconnect(wdt._tabulous_callback)
            except TypeError:
                pass
            wdt.close()

        if widget is None:
            # equivalent to delete the widget
            return None

        if widget.widget_type in ("CheckBox", "RadioButton"):
            converter = lambda x: x != "False"
        elif widget.widget_type in ("SpinBox", "Slider"):
            converter = int
        elif widget.widget_type in ("FloatSpinBox", "FloatSlider"):
            converter = float
        else:
            converter = str

        def _sig():
            with widget.changed.blocked():
                val = self.model().df.iat[r, c]
                try:
                    widget.value = converter(val)
                except Exception:
                    self.setDataFrameValue(r, c, str(widget.value))
                    raise

        if self.model().df.iat[r, c] != "":
            _sig()
        widget.native._tabulous_callback = _sig
        self.itemChangedSignal.connect(_sig)
        widget.changed.connect(lambda val: self.setDataFrameValue(r, c, str(val)))
        self._qtable_view.setIndexWidget(index, widget.native)

    @_set_widget_at_index.server
    def _set_widget_at_index(self, r: int, c: int, widget: ValueWidget):
        index = self.model().index(r, c)
        wdt = self._qtable_view.indexWidget(index)
        return arguments(r, c, getattr(wdt, "_magic_widget", None))

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
            old_name = self._data_raw.columns[index]
            self.setFilter(self._filter_slice)
            super().setHorizontalHeaderValue(index, value)
            if old_name in self._columns_dtype.keys():
                self.setColumnDtype(value, self._columns_dtype.pop(old_name))
            self._data_cache = None

        return None

    @QMutableSimpleTable._mgr.interface
    def setColumnDtype(self, label: Hashable, dtype: Any | None) -> None:
        """Set the dtype of the column with the given label."""
        if dtype is None:
            self._columns_dtype.pop(label, None)

        else:
            if label not in self._data_raw.columns:
                raise ValueError(f"Column {label!r} not found.")

            dtype = get_dtype(dtype)
            if self._columns_dtype.get(label, None) is not dtype:
                self._columns_dtype[label] = dtype
                self._data_cache = None

        if validator := self.model()._validator.get(label, None):
            if isinstance(validator, DefaultValidator):
                self.model()._validator.pop(label)
        if formatter := self.model()._text_formatter.get(label, None):
            if isinstance(formatter, DefaultFormatter):
                self.model()._text_formatter.pop(label)
        return None

    @setColumnDtype.server
    def setColumnDtype(self, label: Hashable, dtype: Any):
        return arguments(label, self._columns_dtype.get(label, None))

    def _set_default_data_validator(self, name: Hashable):
        """Set default data validator based on the dtype."""
        dtype = self._columns_dtype[name]
        validator = DefaultValidator(dtype)
        return self.setDataValidator(name, validator)

    def _set_default_text_formatter(self, name: Hashable):
        """Set default data formatter based on the dtype."""
        dtype = self._columns_dtype[name]
        formatter = DefaultFormatter(dtype)
        return self.setTextFormatter(name, formatter)

    def _install_actions(self):
        # fmt: off
        vheader = self._qtable_view.verticalHeader()
        vheader.registerAction("Insert/Remove > Insert row above")(lambda idx: cmds.selection.insert_row_above(self.parentViewer()._table_viewer))
        vheader.registerAction("Insert/Remove > Insert row below")(lambda idx: cmds.selection.insert_row_below(self.parentViewer()._table_viewer))
        vheader.registerAction("Insert/Remove > Remove this row")(lambda idx: cmds.selection.remove_this_row(self.parentViewer()._table_viewer))
        vheader.registerAction("Insert/Remove > Remove selected rows")(lambda idx: cmds.selection.remove_selected_rows(self.parentViewer()._table_viewer))
        vheader.addSeparator()

        hheader = self._qtable_view.horizontalHeader()
        hheader.registerAction("Insert/Remove > Insert column left")(lambda idx: cmds.selection.insert_column_left(self.parentViewer()._table_viewer))
        hheader.registerAction("Insert/Remove > Insert column right")(lambda idx: cmds.selection.insert_column_right(self.parentViewer()._table_viewer))
        hheader.registerAction("Insert/Remove > Remove this column")(lambda idx: cmds.selection.remove_this_column(self.parentViewer()._table_viewer))
        hheader.registerAction("Insert/Remove > Remove selected columns")(lambda idx: cmds.selection.remove_selected_columns(self.parentViewer()._table_viewer))
        hheader.addSeparator()
        hheader.registerAction("Column dtype")(lambda idx: cmds.selection.set_column_dtype(self.parentViewer()._table_viewer))
        hheader.addSeparator()

        self.registerAction("Insert/Remove > Insert a row above")(lambda idx: cmds.selection.insert_row_above(self.parentViewer()._table_viewer))
        self.registerAction("Insert/Remove > Insert a row below")(lambda idx: cmds.selection.insert_row_below(self.parentViewer()._table_viewer))
        self.registerAction("Insert/Remove > Remove this row")(lambda idx: cmds.selection.remove_this_row(self.parentViewer()._table_viewer))
        self.addSeparator()
        self.registerAction("Insert/Remove > Insert a column on the left")(lambda idx: cmds.selection.insert_column_left(self.parentViewer()._table_viewer))
        self.registerAction("Insert/Remove > Insert a column on the right")(lambda idx: cmds.selection.insert_column_right(self.parentViewer()._table_viewer))
        self.registerAction("Insert/Remove > Remove this column")(lambda idx: cmds.selection.remove_this_column(self.parentViewer()._table_viewer))
        self.addSeparator()

        super()._install_actions()

        self.registerAction("Cell widget > SpinBox")(lambda idx: cmds.selection.add_spinbox(self.parentViewer()._table_viewer))
        self.registerAction("Cell widget > Slider")(lambda idx: cmds.selection.add_slider(self.parentViewer()._table_viewer))
        self.registerAction("Cell widget > FloatSpinBox")(lambda idx: cmds.selection.add_float_spinbox(self.parentViewer()._table_viewer))
        self.registerAction("Cell widget > FloatSlider")(lambda idx: cmds.selection.add_float_slider(self.parentViewer()._table_viewer))
        self.registerAction("Cell widget > CheckBox")(lambda idx: cmds.selection.add_checkbox(self.parentViewer()._table_viewer))
        self.registerAction("Cell widget > RadioButton")(lambda idx: cmds.selection.add_radio_button(self.parentViewer()._table_viewer))
        self.registerAction("Cell widget > LineEdit")(lambda idx: cmds.selection.add_line_edit(self.parentViewer()._table_viewer))
        self.addSeparator("Cell widget ")
        self.registerAction("Cell widget > Remove")(lambda idx: cmds.selection.remove_cell_widgets(self.parentViewer()._table_viewer))

        # fmt: on
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
        # find unique index
        if df.index.size == 0:
            index = range(nr)
        elif isinstance(df.index, (pd.Int64Index, pd.RangeIndex)):
            x0 = int(df.index.max(skipna=True)) + 1
            index = range(x0, x0 + nr)
        else:
            index = range(_nr, _nr + nr)
        ext = _df_full(nr, _nc, value, index=index, columns=df.columns)
        df = pd.concat([df, ext], axis=0)

    # pad columns
    _nr, _nc = df.shape  # NOTE: shape may have changed
    if nc > 0:
        # find unique columns
        if df.columns.size == 0:
            columns = range(nc)
        elif isinstance(df.columns, (pd.Int64Index, pd.RangeIndex)):
            x0 = int(df.columns.max(skipna=True)) + 1
            columns = range(x0, x0 + nc)
        else:
            columns = range(_nc, _nc + nc)
        ext = _df_full(_nr, nc, value, index=df.index, columns=columns)
        df = pd.concat([df, ext], axis=1)

    return df
