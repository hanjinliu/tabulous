from __future__ import annotations

from typing import TYPE_CHECKING, Any, Hashable
import re
from io import StringIO
import warnings

import numpy as np
import pandas as pd
from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt

from collections_undo import arguments

from ._base import AbstractDataFrameModel, QMutableSimpleTable
from ._animation import RowAnimation, ColumnAnimation
from tabulous._dtype import get_converter, get_dtype, DTypeMap, DefaultValidator
from tabulous._utils import TabulousConfig, get_config
from tabulous.color import normalize_color
from tabulous.types import ItemInfo
from tabulous._text_formatter import DefaultFormatter
from tabulous import _pd_index


# More rows/columns will be displayed
_STRING_DTYPE = get_dtype("string")
_EMPTY = object()
_EXP_FLOAT = re.compile(r"[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)")
_FETCH_SIZE = 20


class SpreadSheetModel(AbstractDataFrameModel):
    """A DataFrameModel for a spreadsheet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from tabulous._utils import get_config

        self._table_config = get_config().table
        self._columns_dtype = self.parent()._columns_dtype
        self._out_of_bound_color_cache: QtGui.QColor | None = None
        self._nrows, self._ncols = _FETCH_SIZE * 10, _FETCH_SIZE * 3

    @property
    def _out_of_bound_color(self) -> QtGui.QColor:
        if self._out_of_bound_color_cache is not None:
            return self._out_of_bound_color_cache
        qtable_view = self.parent()._qtable_view
        if viewer := qtable_view.parentViewer():
            bgcolor = viewer.backgroundColor()
        else:
            bgcolor = qtable_view.palette().color(qtable_view.backgroundRole())
        r, g, b = bgcolor.red(), bgcolor.green(), bgcolor.blue()
        if r + b + g > 382.5:
            qcolor = QtGui.QColor(max(r - 4, 0), max(g - 4, 0), b)
        else:
            qcolor = QtGui.QColor(r, g, max(b + 4, 0))
        self._out_of_bound_color_cache = qcolor
        return qcolor

    @property
    def df(self) -> pd.DataFrame:  # NOTE: this returns a string data frame
        return self._df

    @df.setter
    def df(self, data: pd.DataFrame):
        self._df = data

    def rowCount(self, parent=None):
        return self._nrows

    def columnCount(self, parent=None):
        return self._ncols

    def _set_row_count(self, nrows: int):
        _nrows = min(nrows, self._table_config.max_row_count)
        self.setShape(_nrows, self._ncols)
        self._nrows = _nrows

    def _set_column_count(self, ncols: int):
        _ncols = min(ncols, self._table_config.max_column_count)
        self.setShape(self._nrows, _ncols)
        self._ncols = _ncols

    def _data_display(self, index: QtCore.QModelIndex):
        """Display role."""
        r, c = index.row(), index.column()
        df = self.df
        if r < df.shape[0] and c < df.shape[1]:
            val = df.iat[r, c]
            colname = df.columns[c]
            if mapper := self._text_formatter.get(colname, None):
                _converter = get_converter(
                    self._columns_dtype.get(colname, _STRING_DTYPE)
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
                    # since this method is called many times, errorous function should
                    # be deleted from the mapper.
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
            qtable = self.parent()
            r = qtable._proxy.get_source_index(r)
            c = qtable._proxy.get_source_index(c)
            if slot := qtable._qtable_view._table_map.get_by_dest((r, c), None):
                ref = f"\nExpr: {slot.as_literal(dest=True)}"
                if slot._current_error is not None:
                    ref += "\n" + slot.format_error()
            else:
                ref = ""
            dtype = self._columns_dtype.get(name, None)
            val_repr = repr(val)
            if len(val_repr) > 64:
                val_repr = val_repr[:60] + "..." + val_repr[-4:]
            if dtype is None:
                return f"{val_repr} (dtype: infer){ref}"
            else:
                return f"{val_repr} (dtype: {dtype}){ref}"
        return QtCore.QVariant()

    def rename_column(self, old_name: str, new_name: str):
        super().rename_column(old_name, new_name)
        if dtype := self._columns_dtype.pop(old_name, None):
            self._columns_dtype[new_name] = dtype
        return None

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
        from tabulous._utils import get_config

        cfg = get_config()

        if data is not None:
            if (
                cfg.table.max_row_count < data.shape[0]
                or cfg.table.max_column_count < data.shape[1]
            ):
                _max_size = (cfg.table.max_row_count, cfg.table.max_column_count)
                raise ValueError(
                    f"Input table data size {data.shape} exceeds the maximum "
                    f"size {_max_size}."
                )

        self._columns_dtype = DTypeMap()
        super().__init__(parent, data)
        self._qtable_view.verticalHeader().setMinimumWidth(20)
        animate = cfg.window.animate
        self._anim_row = RowAnimation(self).set_animate(animate)
        self._anim_col = ColumnAnimation(self).set_animate(animate)

        # initialize section spans
        rspan, cspan = cfg.table.row_size, cfg.table.column_size
        nr, nc = self._data_raw.shape
        self._qtable_view.verticalHeader().insertSection(0, nr, rspan)
        self._qtable_view.horizontalHeader().insertSection(0, nc, cspan)

        self._qtable_view.verticalScrollBar().valueChanged.connect(self._on_v_scroll)
        self._qtable_view.horizontalScrollBar().valueChanged.connect(self._on_h_scroll)

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
        return self.model().df.shape

    def dataShown(self, parse: bool = False) -> pd.DataFrame:
        """Return the shown dataframe (consider filter)."""
        if parse:
            df = self.getDataFrame()
            df_filt = self._proxy.apply(df)
            if self._column_proxy is not None:
                df_filt = self._column_proxy.apply(df_filt)
            return df_filt
        else:
            return self.model().df

    def load_config(self, cfg: TabulousConfig | None = None):
        """Load new config."""
        self._anim_row.set_animate(cfg.window.animate)
        self._anim_col.set_animate(cfg.window.animate)
        return super().load_config(cfg)

    @QMutableSimpleTable._mgr.interface
    def setDataFrame(self, data: pd.DataFrame) -> None:
        """Set data frame as a string table."""
        self._data_raw = data.astype(_STRING_DTYPE).fillna("")

        # SpreadSheet columns should be str if possible. Convert it.
        if isinstance(self._data_raw.columns, pd.RangeIndex):
            self._data_raw.columns = _pd_index.char_arange(self._data_raw.columns.size)
        elif self._data_raw.columns.dtype.kind in "iuf":
            self._data_raw.columns = self._data_raw.columns.astype(str)

        self._data_cache = None
        self.setProxy(None)
        self.refreshTable()
        return

    def moveToItem(
        self,
        row: int | None = None,
        column: int | None = None,
        clear_selection: bool = True,
    ) -> None:
        """Move current index."""
        model = self.model()
        _need_reset_nrows = False
        _need_reset_ncols = False
        if row is None:
            pass
        elif row < 0:
            _need_reset_nrows = True
            model._set_row_count(model._table_config.max_row_count)
        elif row > model.rowCount():
            model._set_row_count(row + _FETCH_SIZE)
        if column is None:
            pass
        elif column < 0:
            _need_reset_ncols = True
            model._set_column_count(model._table_config.max_column_count)
        elif column > model.columnCount():
            model._set_column_count(column + _FETCH_SIZE)
        super().moveToItem(row, column, clear_selection)
        idx = self._qtable_view._selection_model.current_index
        if _need_reset_nrows:
            model._set_row_count(idx.row + _FETCH_SIZE)
        if _need_reset_ncols:
            model._set_column_count(idx.column + _FETCH_SIZE)
        return None

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
            row_filtered = self.tableSlice()
        else:
            row_filtered = self._proxy.apply(self.tableSlice(), ref=self.getDataFrame)
        return self._column_proxy.apply(row_filtered)

    __delete = object()

    @QMutableSimpleTable._mgr.interface
    def assignColumns(self, serieses: dict[str, pd.Series]):
        to_delete = set()
        to_assign: dict[str, pd.Series] = {}
        for k, v in serieses.items():
            if v is self.__delete:
                to_delete.add(k)
            else:
                to_assign[k] = v.astype(_STRING_DTYPE).fillna("")
        old_value = self._data_raw
        self._data_raw: pd.DataFrame = self._data_raw.assign(**to_assign).drop(
            to_delete, axis=1, inplace=False
        )

        self.model().df = self._data_raw
        self.setProxy(None)
        self.refreshTable()
        # NOTE: ItemInfo cannot have list indices.
        self.itemChangedSignal.emit(
            ItemInfo(
                slice(None),
                slice(None),
                self._data_raw,
                old_value,
            )
        )
        self._data_cache = None
        self._edited = True
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
        keys = list(serieses.keys())
        return f"assign new data to {keys}"

    def _on_v_scroll(self, value: int):
        model = self.model()
        nr = model.rowCount()
        irow = self._qtable_view.rowAt(value + self._qtable_view.height())

        if irow < 0:
            irow = nr - 1
        dr = nr - irow
        if dr < _FETCH_SIZE or dr > _FETCH_SIZE * 2:
            if irow > _FETCH_SIZE * 9:
                model._set_row_count(irow + _FETCH_SIZE)

    def _on_h_scroll(self, value: int):
        model = self.model()
        nc = model.columnCount()
        icol = self._qtable_view.columnAt(value + self._qtable_view.width())

        if icol < 0:
            icol = nc - 1
        dc = nc - icol
        if dc < _FETCH_SIZE or dc > _FETCH_SIZE * 2:
            if icol > _FETCH_SIZE * 2:
                model._set_column_count(icol + _FETCH_SIZE)

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
                # if user start editing an empty cell and did nothing, don't set "NA".
                model = self._qtable_view.model()
                index = model.index(r, c, QtCore.QModelIndex())
                text = model.data(index, Qt.ItemDataRole.DisplayRole)
                if text == value:
                    return

        elif isinstance(value, pd.DataFrame) and any(value.dtypes != "string"):
            value = value.astype(_STRING_DTYPE).fillna("")

        with self._mgr.merging(formatter=lambda _: self._set_value_fmt(r, c, value)):
            if need_expand:
                self.expandDataFrame(max(rmax - nr + 1, 0), max(cmax - nc + 1, 0))
            super().setDataFrameValue(r, c, value)
            self._set_proxy(self._proxy)

        return None

    def setLabeledData(self, r: slice, c: slice, value: pd.Series):
        nr, nc = self._data_raw.shape
        rmax = _get_limit(r)
        cmax = _get_limit(c)
        need_expand = nr <= rmax or nc <= cmax

        if value.dtype != "string":
            value = value.astype(_STRING_DTYPE).fillna("")

        with self._mgr.merging(formatter=lambda cmds: cmds[-2].format()):
            if need_expand:
                self.expandDataFrame(max(rmax - nr + 1, 0), max(cmax - nc + 1, 0))
            super().setLabeledData(r, c, value)
            self._set_proxy(self._proxy)

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
        nr, nc = self._data_raw.shape
        self._data_raw = _pad_dataframe(self._data_raw, nrows, ncols)
        if self._proxy.proxy_type != "none":
            self._set_proxy(self._proxy)  # need update!
        cfg = get_config()

        rspan, cspan = cfg.table.row_size, cfg.table.column_size
        self._qtable_view.verticalHeader().insertSection(nr, nrows, rspan)
        self._qtable_view.horizontalHeader().insertSection(nc, ncols, cspan)
        return None

    @expandDataFrame.undo_def
    def expandDataFrame(self, nrows: int, ncols: int):
        nr, nc = self._data_raw.shape
        self._data_raw = self._data_raw.iloc[: nr - nrows, : nc - ncols]
        self._set_proxy(self._proxy)

        self._qtable_view.verticalHeader().removeSection(nr, nrows)
        self._qtable_view.horizontalHeader().insertSection(nc, ncols)
        self._data_cache = None
        return None

    @QMutableSimpleTable._mgr.undoable
    def insertRows(
        self, row: int, count: int, value: Any = _EMPTY, span: int | None = None
    ):
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
        if _pd_index.is_ranged(index_existing):
            self._data_raw.index = pd.RangeIndex(0, self._data_raw.index.size)
        self.model().insertRows(row, count, QtCore.QModelIndex(), span=span)

        @self._anim_row.connect
        def _on_finish():
            self._set_proxy(self._proxy)
            self._data_cache = None
            self._edited = True

            # update indices
            self._process_insert_rows(row, count)

            info = ItemInfo(
                slice(row, row + count),
                slice(None),
                value,
                ItemInfo.INSERTED,
            )
            self._qtable_view.setZoom(self._qtable_view.zoom())
            self.itemChangedSignal.emit(info)

        return self._anim_row.run_insert(row, count, span)

    @insertRows.undo_def
    def insertRows(self, row: int, count: int, value: Any = _EMPTY, span=None):
        """Insert rows at the given row number and count."""
        return self.removeRows(row, count)

    @insertRows.set_formatter
    def _insertRows_fmt(self, row: int, count: int, value: Any = _EMPTY):
        return f"table.index.insert(at={row}, count={count})"

    def insertColumns(
        self, col: int, count: int, value: Any = _EMPTY, span: int | None = None
    ):
        """Insert columns at the given column number and count."""
        with self._mgr.merging(
            lambda cmds: f"table.columns.insert(at={col}, count={count})"
        ):
            self._insert_columns(col, count, value, span)
            self._process_header_widgets_on_insert(col, count)
        return None

    @QMutableSimpleTable._mgr.undoable
    def _insert_columns(
        self, col: int, count: int, value: Any = _EMPTY, span: int | None = None
    ):
        columns_existing = self._data_raw.columns
        _c_ranged = _pd_index.is_ranged(columns_existing)

        if value is _EMPTY:
            columns = _remove_duplicate(
                _pd_index.char_arange(col, col + count), existing=columns_existing
            )
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
        # if column index is ranged chars, re-assign them
        if _c_ranged:
            self._data_raw.columns = _pd_index.char_range_index(
                self._data_raw.columns.size
            )
            model = self.model()
            for d in [
                model._foreground_colormap,
                model._background_colormap,
                model._text_formatter,
                model._validator,
                self._columns_dtype,
            ]:
                _inserte_in_dict(d, col, count)

        self.model().insertColumns(col, count, QtCore.QModelIndex(), span=span)

        @self._anim_col.connect
        def _on_finish():
            self._data_cache = None
            self._edited = True

            # update indices
            self._process_insert_columns(col, count)

            info = ItemInfo(
                slice(None),
                slice(col, col + count),
                value,
                ItemInfo.INSERTED,
            )
            self._qtable_view.setZoom(self._qtable_view.zoom())
            self.itemChangedSignal.emit(info)

        return self._anim_col.run_insert(col, count, span)

    @_insert_columns.undo_def
    def _insert_columns(self, col: int, count: int, value: Any = _EMPTY, span=None):
        """Insert columns at the given column number and count."""
        self._remove_columns(col, count, self._data_raw.iloc[:, col : col + count])
        self._set_proxy(self._proxy)
        return None

    def removeRows(self, row: int, count: int):
        """Remove rows at the given row number and count."""
        df = self.model().df.iloc[row : row + count, :]
        hheader = self._qtable_view.verticalHeader()
        spans = hheader._section_sizes[row : row + count].copy()
        with self._mgr.merging(
            lambda cmds: f"table.index.remove(at={row}, count={count})"
        ):
            self._clear_incell_slots(
                slice(row, row + count),
                slice(0, self._data_raw.shape[1]),
            )
            self._remove_rows(row, count, df, spans)
        return None

    @QMutableSimpleTable._mgr.undoable
    def _remove_rows(self, row: int, count: int, old_values: pd.DataFrame, spans=None):
        _r_ranged = isinstance(self._data_raw.index, pd.RangeIndex)
        _new_data_raw = pd.concat(
            [self._data_raw.iloc[:row, :], self._data_raw.iloc[row + count :, :]],
            axis=0,
        )
        if _r_ranged:
            _new_data_raw.index = pd.RangeIndex(0, _new_data_raw.index.size)

        @self._anim_row.connect
        def _on_finish():
            self._data_raw = _new_data_raw
            self.model().removeRows(row, count, QtCore.QModelIndex())
            self._set_proxy(self._proxy)
            self.setSelections(
                [(slice(row, row + 1), slice(0, self._data_raw.shape[1]))]
            )
            self._data_cache = None
            self._edited = True

            self._process_remove_rows(row, count)
            info = ItemInfo(
                slice(row, row + count), slice(None), ItemInfo.DELETED, old_values
            )
            self._qtable_view.setZoom(self._qtable_view.zoom())
            self.itemChangedSignal.emit(info)

        self._anim_row.run_remove(row, count)
        return None

    @_remove_rows.undo_def
    def _remove_rows(self, row: int, count: int, old_values: pd.DataFrame, spans=None):
        self.insertRows(row, count, old_values, spans)
        self.setSelections([(slice(row, row + 1), slice(0, self._data_raw.shape[1]))])
        return None

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
            model = self.model()
            hheader = self._qtable_view.horizontalHeader()
            for index in range(column, column + count):
                colname = model.df.columns[index]
                self.setForegroundColormap(colname, None)
                self.setBackgroundColormap(colname, None)
                self.setTextFormatter(colname, None)
                self.setDataValidator(colname, None)
                self.setColumnDtype(colname, None)
            section_sizes = hheader._section_sizes[column : column + count].copy()
            self._remove_columns(column, count, df, section_sizes)
        return None

    @QMutableSimpleTable._mgr.undoable
    def _remove_columns(
        self,
        col: int,
        count: int,
        old_values: pd.DataFrame,
        spans: np.ndarray | None = None,
    ):
        _c_ranged = _pd_index.is_ranged(self._data_raw.columns)
        _new_data_raw = pd.concat(
            [self._data_raw.iloc[:, :col], self._data_raw.iloc[:, col + count :]],
            axis=1,
        )
        if _c_ranged:
            _new_data_raw.columns = _pd_index.char_range_index(
                _new_data_raw.columns.size
            )
            model = self.model()
            for d in [
                model._foreground_colormap,
                model._background_colormap,
                model._text_formatter,
                model._validator,
                self._columns_dtype,
            ]:
                _remove_in_dict(d, col, count)

        @self._anim_col.connect
        def _on_finish():
            self.model().removeColumns(col, count, QtCore.QModelIndex())
            self._data_raw = _new_data_raw
            self.setSelections(
                [(slice(0, self._data_raw.shape[0]), slice(col, col + 1))]
            )
            self._data_cache = None
            self._edited = True

            self._process_remove_columns(col, count)
            self._qtable_view.setZoom(self._qtable_view.zoom())
            info = ItemInfo(
                slice(None), slice(col, col + count), ItemInfo.DELETED, old_values
            )
            self.itemChangedSignal.emit(info)  # relay to the psygnal.Signal
            self._set_proxy(self._proxy)
            return

        self._anim_col.run_remove(col, count)
        return None

    @_remove_columns.undo_def
    def _remove_columns(
        self,
        col: int,
        count: int,
        old_values: pd.DataFrame,
        spans: np.ndarray | None = None,
    ):
        self.insertColumns(col, count, old_values, spans)
        self.setSelections([(slice(0, self._data_raw.shape[0]), slice(col, col + 1))])
        return None

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
        self._set_proxy(self._proxy)
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
        return _df_full(nr, nc, value, columns=_pd_index.char_range_index(nc))

    # pad rows
    _nr, _nc = df.shape
    _r_ranged = isinstance(df.index, pd.RangeIndex)
    _c_ranged = _pd_index.is_ranged(df.columns)
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
        columns = _pd_index.char_arange(df.columns.size, df.columns.size + nc)
        # check duplication
        if not _c_ranged:
            columns = _remove_duplicate(columns, existing=df.columns)
        ext = _df_full(_nr, nc, value, index=df.index, columns=columns)
        df = pd.concat([df, ext], axis=1)
        if _c_ranged:
            df.columns = _pd_index.char_range_index(df.columns.size)
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


def _remove_duplicate(
    columns: np.ndarray,
    existing: pd.Index,
    copy: bool = False,
) -> np.ndarray:
    """Remove names from `columns` that have duplicates in `existing`"""
    if copy:
        columns = columns.copy()
    for ic, c in enumerate(columns):
        if c in existing:
            i = 0
            c0 = f"{c}_{i}"
            while c0 in existing:
                i += 1
                c0 = f"{c}_{i}"
            columns[ic] = c0
    return columns


def _inserte_in_dict(d: dict[str, Any], start: int, count: int) -> None:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if _pd_index.str_to_num(k) >= start:
            out[_pd_index.increment(k, count)] = v
        else:
            out[k] = v
    d.clear()
    d.update(out)
    return None


def _remove_in_dict(d: dict[str, Any], start: int, count: int) -> None:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if _pd_index.str_to_num(k) >= start + count:
            out[_pd_index.decrement(k, count)] = v
        else:
            out[k] = v
    d.clear()
    d.update(out)
    return None
