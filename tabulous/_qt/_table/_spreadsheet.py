from __future__ import annotations

from typing import TYPE_CHECKING, Any, Hashable
import re
from functools import cached_property
from io import StringIO
import warnings

import numpy as np
import pandas as pd
from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt

from collections_undo import arguments

from ._base import AbstractDataFrameModel, QMutableSimpleTable
from tabulous._dtype import get_converter, get_dtype, DTypeMap, DefaultValidator
from tabulous.color import normalize_color
from tabulous.types import ItemInfo
from tabulous._text_formatter import DefaultFormatter
from tabulous._pd_index import char_range_index, is_ranged, char_arange

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
        color = self.parent()._qtable_view.parentViewer().backgroundColor()
        r, g, b = color.red(), color.green(), color.blue()
        return QtGui.QColor(max(r - 4, 0), max(g - 4, 0), b)

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
            out.columns = data_raw.columns
        else:
            out = pd.DataFrame(index=data_raw.index, columns=[])
        self._data_cache = out
        return out

    def _get_sub_frame(self, columns: list[str]) -> pd.DataFrame:
        """Parse and return a sub-frame of the table."""
        if self._data_cache is not None:
            return self._data_cache[columns]
        is_series = not isinstance(columns, list)
        if is_series:
            columns = [columns]
        _sep = "\t"
        data_raw = self._data_raw[columns]
        _dtype_map = self._columns_dtype.copy()
        _to_be_deleted = []
        for key in _dtype_map:
            if key not in columns:
                _to_be_deleted.append(key)
        for key in _to_be_deleted:
            del _dtype_map[key]

        val = data_raw.to_csv(sep=_sep, index=False)
        buf = StringIO(val)
        out: pd.DataFrame = pd.read_csv(
            buf,
            sep=_sep,
            header=0,
            na_values=["#ERROR"],
            names=data_raw.columns,
            **_dtype_map.as_pandas_kwargs(),
        )
        out.index = data_raw.index
        if is_series:
            out = out.iloc[:, 0]
        return out

    def dataShape(self) -> tuple[int, int]:
        """Shape of data."""
        return self._data_raw.shape

    def dataShown(self, parse: bool = False) -> pd.DataFrame:
        """Return the shown dataframe (consider filter)."""
        if parse:
            df = self.getDataFrame()
            return self._proxy.apply(df)
        else:
            return self.model().df

    @QMutableSimpleTable._mgr.interface
    def setDataFrame(self, data: pd.DataFrame) -> None:
        """Set data frame as a string table."""
        self._data_raw = data.astype(_STRING_DTYPE)

        # SpreadSheet columns should be str if possible. Convert it.
        if isinstance(self._data_raw.columns, pd.RangeIndex):
            self._data_raw.columns = char_arange(self._data_raw.columns.size)
        elif self._data_raw.columns.dtype.kind in "iuf":
            self._data_raw.columns = self._data_raw.columns.astype(str)

        self.model().setShape(
            data.index.size + _OUT_OF_BOUND_R,
            data.columns.size + _OUT_OF_BOUND_C,
        )
        self._data_cache = None
        self.setProxy(None)
        self.refreshTable()
        return

    def updateValue(self, r, c, val):
        index = self._data_raw.index[r]
        columns = self._data_raw.columns[c]
        # NOTE: It seems very weird but the string array of pandas does not
        # support setting (N, 1) string array.
        if isinstance(val, pd.DataFrame):
            # NOTE loc-indexer takes axes into consideration. Here, input data
            # frame needs to be updated.
            val.index = index
            val.columns = columns
            if isinstance(c, slice) and c.stop == 1:
                val = pd.Series(val.iloc[:, 0], dtype="string")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._data_raw.loc[index, columns] = val
        if self._proxy.proxy_type != "none":
            self._set_proxy(self._proxy)
        return self.refreshTable()

    @setDataFrame.server
    def setDataFrame(self, data):
        return arguments(getattr(self, "_data_raw", None))

    @setDataFrame.set_formatter
    def _setDataFrame_fmt(self, data: pd.DataFrame):
        return f"set new data of shape {data.shape}"

    def _apply_proxy(self):
        if self._proxy.proxy_type == "none":
            return self.tableSlice()
        return self._proxy.apply(self.tableSlice(), ref=self.getDataFrame)

    def _get_proxy_source_index(self, r: int):
        if self._proxy.proxy_type == "none":
            return self._proxy.get_source_index(r, self.tableSlice())
        return self._proxy.get_source_index(r, self.getDataFrame())

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
        self.setProxy(None)
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
            self._set_proxy(self._proxy)

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
            self._set_proxy(self._proxy)

        self._qtable_view.verticalHeader().resize(
            self._qtable_view.verticalHeader().sizeHint()
        )
        return None

    def _pre_set_array(self, r: slice, c: slice, _value: pd.DataFrame):
        """Convert input dataframe for setting to data[r, c]."""
        if len(self.model()._validator) == 0:
            # use faster method if no validator is set
            out = self._data_raw.iloc[r, c].copy()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if _value.size == 1:
                    val = _value.values[0, 0]
                    if val == "NA":
                        val = ""
                    out.loc[:, :] = val
                else:
                    out.loc[:, :] = _value.astype(_STRING_DTYPE).fillna("").values
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
        self._set_proxy(self._proxy)
        self._data_cache = None
        return None

    @QMutableSimpleTable._mgr.undoable
    def insertRows(self, row: int, count: int, value: Any = _EMPTY):
        """Insert rows at the given row number and count."""
        if self._proxy.proxy_type != "none":
            raise NotImplementedError("Cannot insert rows during filtering/sorting.")

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
        if is_ranged(index_existing):
            self._data_raw.index = pd.RangeIndex(0, self._data_raw.index.size)
        self.model().insertRows(row, count, QtCore.QModelIndex())
        self._set_proxy(self._proxy)
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
        return f"table.index.insert(at={row}, count={count})"

    def insertColumns(self, col: int, count: int, value: Any = _EMPTY):
        """Insert columns at the given column number and count."""
        with self._mgr.merging(
            lambda cmds: f"table.columns.insert(at={col}, count={count})"
        ):
            self._insert_columns(col, count, value)
            self._process_header_widgets_on_insert(col, count)
            self._set_proxy(self._proxy)
        return None

    @QMutableSimpleTable._mgr.undoable
    def _insert_columns(self, col: int, count: int, value: Any = _EMPTY):
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
        if is_ranged(columns_existing):
            self._data_raw.columns = char_range_index(self._data_raw.columns.size)
        self.model().insertColumns(col, count, QtCore.QModelIndex())
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

    @_insert_columns.undo_def
    def _insert_columns(self, col: int, count: int, value: Any = _EMPTY):
        """Insert columns at the given column number and count."""
        return self.removeColumns(col, count)

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
        _r_ranged = isinstance(self._data_raw.index, pd.RangeIndex)
        self._data_raw = pd.concat(
            [self._data_raw.iloc[:row, :], self._data_raw.iloc[row + count :, :]],
            axis=0,
        )
        if _r_ranged:
            self._data_raw.index = pd.RangeIndex(0, self._data_raw.index.size)
        self.model().removeRows(row, count, QtCore.QModelIndex())
        self._set_proxy(self._proxy)
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
        return f"table.index.remove(at={row}, count={count})"

    def removeColumns(self, column: int, count: int):
        """Remove columns at the given column number and count."""
        df = self.model().df.iloc[:, column : column + count]
        with self._mgr.merging(
            lambda cmds: f"table.columns.remove(at={column}, count={count})"
        ):
            self._clear_incell_slots(
                slice(0, self._data_raw.shape[0]),
                slice(column, column + count),
            )
            self._process_header_widgets_on_remove(column, count)
            self._remove_columns(column, count, df)
            self._set_proxy(self._proxy)
        return None

    @QMutableSimpleTable._mgr.undoable
    def _remove_columns(self, col: int, count: int, old_values: pd.DataFrame):
        _c_ranged = is_ranged(self._data_raw.columns)
        model = self.model()
        for index in range(col, col + count):
            colname = model.df.columns[index]
            model.delete_column(colname)
            self._columns_dtype.pop(colname, None)

        self._data_raw = pd.concat(
            [self._data_raw.iloc[:, :col], self._data_raw.iloc[:, col + count :]],
            axis=1,
        )
        if _c_ranged:
            self._data_raw.columns = char_range_index(self._data_raw.columns.size)
        self.model().removeColumns(col, count, QtCore.QModelIndex())
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
            self._set_proxy(self._proxy)
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
            self._set_proxy(self._proxy)
            super().setHorizontalHeaderValue(index, value)
            if old_name in self._columns_dtype.keys():
                self.setColumnDtype(value, self._columns_dtype.pop(old_name))
            self._data_cache = None

        return None

    @QMutableSimpleTable._mgr.interface
    def setColumnDtype(self, label: Hashable, dtype: Any | None) -> None:
        """Set the dtype of the column with the given label."""
        if dtype is None:
            # delete cache if dtype used to be set
            if self._columns_dtype.pop(label, None):
                self._data_cache = None
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

    def _process_header_widgets_on_insert(self, column: int, count: int):
        to_increment: list[int] = []
        header_widgets = self._header_widgets().copy()
        for k in header_widgets.keys():
            if k >= column:
                to_increment.append(k)
        to_increment.sort(reverse=True)
        for k in to_increment:
            header_widgets[k + count] = header_widgets.pop(k)
        self.updateHorizontalHeaderWidget(header_widgets)
        return None

    def _process_header_widgets_on_remove(self, column: int, count: int):
        to_remove: list[int] = []
        to_decrement: list[int] = []
        header_widgets = self._header_widgets().copy()
        for k in header_widgets.keys():
            if k >= column:
                if k < column + count:
                    to_remove.append(k)
                else:
                    to_decrement.append(k)
        for k in to_remove:
            header_widgets.pop(k)
        to_decrement.sort()
        for k in to_decrement:
            header_widgets[k - count] = header_widgets.pop(k)
        self.updateHorizontalHeaderWidget(header_widgets)
        return None


def _pad_dataframe(df: pd.DataFrame, nr: int, nc: int, value: Any = "") -> pd.DataFrame:
    """Pad a dataframe by nr rows and nr columns with the given value."""
    if df.shape == (0, 0):
        return _df_full(nr, nc, value, columns=char_range_index(nc))

    # pad rows
    _nr, _nc = df.shape
    _r_ranged = isinstance(df.index, pd.RangeIndex)
    _c_ranged = is_ranged(df.columns)
    if nr > 0:
        # find unique index
        if df.index.size == 0:
            index = range(nr)
        else:
            index = range(_nr, _nr + nr)
        ext = _df_full(nr, _nc, value, index=index, columns=df.columns)
        df = pd.concat([df, ext], axis=0)
        if _r_ranged:
            df.index = pd.RangeIndex(0, df.index.size)

    # pad columns
    _nr, _nc = df.shape  # NOTE: shape may have changed
    if nc > 0:
        # find unique columns
        if df.columns.size == 0:
            columns = char_arange(nc)
        else:
            columns = char_arange(_nc, _nc + nc)
        # check duplication
        if not _c_ranged:
            _old_columns = df.columns
            for ic, c in enumerate(columns):
                if c in _old_columns:
                    i = 0
                    c0 = f"{c}_{i}"
                    while c0 in _old_columns:
                        i += 1
                        c0 = f"{c}_{i}"
                    columns[ic] = c0
        ext = _df_full(_nr, nc, value, index=df.index, columns=columns)
        df = pd.concat([df, ext], axis=1)
        if _c_ranged:
            df.columns = char_range_index(df.columns.size)
    return df


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
