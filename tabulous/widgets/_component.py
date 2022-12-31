from __future__ import annotations
from abc import abstractmethod
from contextlib import contextmanager
import weakref
from typing import (
    Generic,
    Hashable,
    Literal,
    TYPE_CHECKING,
    Mapping,
    MutableSequence,
    Sequence,
    TypeVar,
    Tuple,
    overload,
    Any,
    Callable,
    Union,
    MutableMapping,
    Iterator,
)

import numpy as np
from qtpy.sip import isdeleted
from magicgui.widgets import Widget
from tabulous.exceptions import TableImmutableError
from tabulous.types import _SingleSelection, SelectionType, EvalInfo, ProxyType
from tabulous._psygnal import InCellRangedSlot

if TYPE_CHECKING:
    from typing_extensions import Self
    from numpy.typing import NDArray
    import pandas as pd
    from pandas.core.dtypes.dtypes import ExtensionDtype
    from tabulous.widgets._table import TableBase, SpreadSheet
    from tabulous._qt._table._base._header_view import QDataFrameHeaderView

    _DtypeLike = Union[np.dtype, ExtensionDtype]
    _SortArray = NDArray[np.integer]
    _FilterArray = NDArray[np.bool_]

T = TypeVar("T")
_F = TypeVar("_F", bound=Callable)


class _NoRef:
    """No reference."""


class Component(Generic[T]):
    _no_ref = _NoRef()

    def __init__(self, parent: T | _NoRef = _no_ref):
        if parent is self._no_ref:
            self._instances: dict[int, Self] = {}
        else:
            self._instances = None
        self._parent_ref = weakref.ref(parent)

    @property
    def parent(self) -> T:
        """The parent object of this component."""
        out = self._parent_ref()
        if out is None:
            raise ReferenceError("Parent has been garbage collected.")
        return out

    def __repr__(self) -> str:
        return f"<{type(self).__name__} of {self.parent!r}>"

    @overload
    def __get__(self, obj: Literal[None], owner=None) -> Self[_NoRef]:
        ...

    @overload
    def __get__(self, obj: T, owner=None) -> Self[T]:
        ...

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        _id = id(obj)
        if (out := self._instances.get(_id)) is None:
            out = self._instances[_id] = self.__class__(obj)
        return out

    def __set__(self, obj: T, value: Any) -> None:
        if obj is None:
            raise AttributeError("Cannot set attribute.")
        _id = id(obj)
        if (ins := self._instances.get(_id)) is None:
            ins = self._instances[_id] = self.__class__(obj)

        return ins._set_value(value)

    def _set_value(self, value: Any):
        raise AttributeError("Cannot set attribute.")


class _TableComponent(Component["TableBase"]):
    def _assert_spreadsheet(self) -> SpreadSheet:
        sheet = self.parent
        if sheet.table_type != "SpreadSheet":
            raise TypeError(
                f"{sheet.table_type!r} does not support insert. Use "
                "SpreadSheet instead."
            )
        return sheet


class _HeaderInterface(_TableComponent):
    def _get_axis(self) -> pd.Index:
        raise NotImplementedError()

    def _set_value(self, idx: int, val: Any):
        raise NotImplementedError()

    def _get_header(self) -> QDataFrameHeaderView:
        raise NotImplementedError()

    def __repr__(self) -> str:
        return f"<{type(self).__name__}({self._get_axis()!r}) of {self.parent!r}>"

    def __getitem__(self, key: int | slice):
        return self._get_axis()[key]

    def __setitem__(self, key: int | slice, value: Any):
        table = self.parent
        if not table.editable:
            raise TableImmutableError("Table is not editable.")

        if isinstance(key, slice):
            start, stop, step = key.indices(len(self._get_axis()))
            for i, idx in enumerate(range(start, stop, step)):
                self._set_value(idx, value[i])
        else:
            idx = key.__index__()
            self._set_value(idx, value)
        return None

    def __len__(self) -> int:
        return len(self._get_axis())

    def __iter__(self) -> Iterator[str]:
        return iter(self._get_axis())

    def __contains__(self, key: str) -> bool:
        return key in self._get_axis()

    def __eq__(self, other: Sequence[str]) -> np.ndarray:
        return self._get_axis() == other

    @property
    def str(self):
        return self._get_axis().str

    def get_loc(self, key: str) -> int:
        """Get the location of a column."""
        return self._get_axis().get_loc(key)

    def isin(self, values) -> np.ndarray:
        """Return a boolean array of whether each value is found in the passed values."""
        return self._get_axis().isin(values)

    def coerce_name(self, name: str, start: int | None = None) -> str:
        """Coerce a name to avoid name collision."""
        index = self._get_axis()
        i = 0
        if start is not None:
            name = f"{name}_{start}"
            i = start + 1
        while name in index:
            name = f"{name}_{i}"
            i += 1
        return name

    # fmt: off
    @overload
    def register_action(self, val: str) -> Callable[[_F], _F]: ...
    @overload
    def register_action(self, val: _F) -> _F: ...
    # fmt: on

    def register_action(self, val: str | Callable[[int], Any]):
        """Register an contextmenu action to the tablelist."""
        header = self._get_header()
        if isinstance(val, str):
            return header.registerAction(val)
        elif callable(val):
            location = val.__name__.replace("_", " ")
            return header.registerAction(location)(val)
        else:
            raise ValueError("input must be a string or callable.")


class VerticalHeaderInterface(_HeaderInterface):
    """The interface for the vertical header of the tablelist."""

    def _get_axis(self) -> pd.Index:
        return self.parent._qwidget.model().df.index

    def _set_value(self, idx: int, val: Any):
        return self.parent._qwidget.setVerticalHeaderValue(idx, val)

    def _get_header(self) -> QDataFrameHeaderView:
        return self.parent._qwidget._qtable_view.verticalHeader()

    @property
    def selected(self) -> list[slice]:
        """Return the selected row ranges."""
        smodel = self.parent._qwidget._qtable_view._selection_model
        out = [smodel.ranges[i][0] for i in smodel._row_selection_indices]
        return out

    def insert(self, at: int, count: int):
        """Insert `count` rows at the given position."""
        sheet = self._assert_spreadsheet()
        sheet._qwidget.insertRows(at, count)

    def remove(self, at: int, count: int):
        """Remove `count` rows at the given position."""
        sheet = self._assert_spreadsheet()
        sheet._qwidget.removeRows(at, count)


class HorizontalHeaderInterface(_HeaderInterface):
    """The interface for the horizontal header of the tablelist."""

    def _get_axis(self) -> pd.Index:
        return self.parent._qwidget.model().df.columns

    def _set_value(self, idx: int, val: Any):
        return self.parent._qwidget.setHorizontalHeaderValue(idx, val)

    def _get_header(self) -> QDataFrameHeaderView:
        return self.parent._qwidget._qtable_view.horizontalHeader()

    @property
    def selected(self) -> list[slice]:
        """Return the selected row ranges."""
        smodel = self.parent._qwidget._qtable_view._selection_model
        out = [smodel.ranges[i][1] for i in smodel._col_selection_indices]
        return out

    def insert(self, at: int, count: int):
        """Insert `count` columns at the given position."""
        sheet = self._assert_spreadsheet()
        sheet._qwidget.insertColumns(at, count)

    def remove(self, at: int, count: int):
        """Remove `count` columns at the given position."""
        sheet = self._assert_spreadsheet()
        sheet._qwidget.removeColumns(at, count)


class CellInterface(_TableComponent):
    """The interface for editing cell as if it was manually edited."""

    def __getitem__(self, key: tuple[int | slice, int | slice]):
        return self.parent._qwidget.model().df.iloc[key]

    def __setitem__(self, key: tuple[int | slice, int | slice], value: Any) -> None:
        table = self.parent
        if not table.editable:
            raise TableImmutableError("Table is not editable.")

        if isinstance(value, Widget):
            # add item widget
            r, c = key
            if isinstance(r, int) and isinstance(c, int):
                sheet = self._assert_spreadsheet()
                return sheet._qwidget._set_widget_at_index(*key, value)
            raise TypeError("Cannot set widget at slices.")

        import pandas as pd
        from tabulous._qt._table._base._line_edit import QCellLiteralEdit

        row, col = self._normalize_key(key)

        if isinstance(value, str) and QCellLiteralEdit._is_eval_like(value):
            if row.stop - row.start == 1 and col.stop - col.start == 1:
                expr, is_ref = QCellLiteralEdit._parse_ref(value)
                info = EvalInfo(
                    row=row.start,
                    column=col.start,
                    expr=expr,
                    is_ref=is_ref,
                )
                table.events.evaluated.emit(info)
                return None
            else:
                raise ValueError("Cannot evaluate a multi-cell selection.")

        if isinstance(value, str) or not hasattr(value, "__iter__"):
            _value = [[value]]
        else:
            _value = value
        try:
            df = pd.DataFrame(_value)
        except ValueError:
            raise ValueError(f"Could not convert value {_value!r} to DataFrame.")

        if 1 in df.shape and (col.stop - col.start, row.stop - row.start) == df.shape:
            # it is natural to set an 1-D array without thinking of the direction.
            df = df.T

        table._qwidget.setDataFrameValue(row, col, df)
        return None

    def __delitem__(self, key: tuple[int | slice, int | slice]) -> None:
        """Deleting cell, equivalent to pushing Delete key."""

        table = self.parent
        if not table.editable:
            raise TableImmutableError("Table is not editable.")
        row, col = key
        table._qwidget.setSelections([(row, col)])
        table._qwidget.deleteValues()
        return None

    def _normalize_key(
        self,
        key: tuple[int | slice, int | slice],
    ) -> tuple[slice, slice]:
        if len(key) == 1:
            key = (key, slice(None))
        row, col = key

        if isinstance(row, slice):
            row = _normalize_slice(row, self.parent._qwidget.model().df.shape[0])
        else:
            row = slice(row, row + 1)

        if isinstance(col, slice):
            col = _normalize_slice(col, self.parent._qwidget.model().df.shape[1])
        else:
            col = slice(col, col + 1)
        return row, col

    # fmt: off
    @overload
    def register_action(self, val: str) -> Callable[[_F], _F]: ...
    @overload
    def register_action(self, val: _F) -> _F: ...
    # fmt: on

    def register_action(self, val: str | Callable[[tuple[int, int]], Any]):
        """Register an contextmenu action to the tablelist."""
        table = self.parent.native
        if isinstance(val, str):
            return table.registerAction(val)
        elif callable(val):
            location = val.__name__.replace("_", " ")
            return table.registerAction(location)(val)
        else:
            raise TypeError("input must be a string or callable.")

    def get_label(self, r: int, c: int) -> str | None:
        """Get the label of a cell."""
        return self.parent.native.itemLabel(r, c)

    def set_label(self, r: int, c: int, text: str):
        """Set the label of a cell."""
        return self.parent.native.setItemLabel(r, c, text)

    def set_labeled_data(
        self,
        r: int,
        c: int,
        data: dict[str, Any] | pd.Series | tuple,
        sep: str = "",
    ):
        """
        Set given data with cell labels.

        Parameters
        ----------
        r : int
            Starting row index.
        c : int
            Starting column index.
        data : dict[str, Any], pd.Series or (named) tuple
            Data to be set.
        sep : str, optional
            Separator added at the end of labels.
        """
        import pandas as pd

        ndata = len(data)
        if isinstance(data, dict):
            _data = pd.Series(data)
        elif isinstance(data, tuple):
            index = getattr(data, "_fields", range(ndata))
            _data = pd.Series(data, index=index)
        elif isinstance(data, pd.Series):
            _data = data.copy()
        else:
            raise TypeError(f"Cannot convert {data!r} to Series.")

        if sep:
            _data.index = [f"{idx}{sep}" for idx in _data.index]

        self.parent._qwidget.setLabeledData(slice(r, r + ndata), slice(c, c + 1), _data)
        return None


def _plt_function(name: str, method_name: str | None = None):
    """Make a function that calls ``plt.<name>`` on the current figure."""
    if method_name is None:
        method_name = name

    def func(self: PlotInterface, *args, **kwargs):
        ax = self.gca()
        out = getattr(ax, method_name)(*args, picker=True, **kwargs)
        self.draw()
        return out

    func.__name__ = name
    func.__qualname__ = f"PlotInterface.{name}"
    func.__doc__ = f"Call ``plt.{name}`` on the current figure."
    return func


class PlotInterface(_TableComponent):
    """The interface of plotting."""

    def __init__(self, parent=Component._no_ref):
        super().__init__(parent)
        self._current_widget = None

    def gcf(self):
        """Get current figure."""
        return self.gcw().figure

    def gca(self):
        """Get current axis."""
        return self.gcw().ax

    def gcw(self):
        """Get current widget."""
        if self._current_widget is None or isdeleted(self._current_widget):
            self.new_widget()
        return self._current_widget

    def new_widget(self, nrows=1, ncols=1):
        """Create a new plot widget and add it to the table."""
        from tabulous._qt._plot import QtMplPlotCanvas

        table = self.parent
        qviewer = table._qwidget._qtable_view.parentViewer()
        if qviewer._white_background:
            style = None
        else:
            style = "dark_background"

        wdt = QtMplPlotCanvas(nrows=nrows, ncols=ncols, style=style)
        wdt.set_background_color(qviewer.backgroundColor().name())
        wdt.canvas.deleteRequested.connect(self.delete_widget)
        table.add_side_widget(wdt, name="Plot")
        self._current_widget = wdt
        return wdt

    def delete_widget(self) -> None:
        """Delete the current widget from the side area."""
        if self._current_widget is None:
            return None
        try:
            self.parent._qwidget._side_area.removeWidget(self._current_widget)
        except Exception:
            pass
        self._current_widget.deleteLater()
        self._current_widget = None
        return None

    def figure(self, style=None):
        return self.subplots(style=style)[0]

    def subplots(self, nrows=1, ncols=1, style=None):
        wdt = self.new_widget(nrows=nrows, ncols=ncols, style=style)
        return wdt.figure, wdt.axes

    plot = _plt_function("plot")
    plot_date = _plt_function("plot_date")
    quiver = _plt_function("quiver")
    scatter = _plt_function("scatter")
    bar = _plt_function("bar")
    errorbar = _plt_function("errorbar")
    hist = _plt_function("hist")
    text = _plt_function("text")
    fill_between = _plt_function("fill_between")
    fill_betweenx = _plt_function("fill_betweenx")

    def xlabel(self, *args, **kwargs):
        """Call ``plt.xlabel`` on the current side figure."""
        if not args and not kwargs:
            return self.gca().get_xlabel()
        out = self.gca().set_xlabel(*args, **kwargs)
        self.draw()
        return out

    def ylabel(self, *args, **kwargs):
        """Call ``plt.ylabel`` on the current side figure."""
        if not args and not kwargs:
            return self.gca().get_ylabel()
        out = self.gca().set_ylabel(*args, **kwargs)
        self.draw()
        return out

    def xlim(self, *args, **kwargs):
        """Call ``plt.xlim`` on the current side figure."""
        if not args and not kwargs:
            return self.gca().get_xlim()
        out = self.gca().set_xlim(*args, **kwargs)
        self.draw()
        return out

    def ylim(self, *args, **kwargs):
        """Call ``plt.ylim`` on the current side figure."""
        if not args and not kwargs:
            return self.gca().get_ylim()
        out = self.gca().set_ylim(*args, **kwargs)
        self.draw()
        return out

    def title(self, *args, **kwargs):
        """Call ``plt.title`` on the current side figure."""
        if not args and not kwargs:
            return self.gca().get_title()
        out = self.gca().set_title(*args, **kwargs)
        self.draw()
        return out

    def draw(self):
        """Update the current side figure."""
        return self._current_widget.draw()

    @property
    def background_color(self):
        """Background color of the current figure."""
        return self.gcf().get_facecolor()

    @background_color.setter
    def background_color(self, color):
        """Set background color of the current figure."""
        return self.gcw().set_background_color(color)


_Range = Tuple[slice, slice]


class _TableRanges(_TableComponent, MutableSequence[_Range]):
    def __init__(self, parent: T | _NoRef = Component._no_ref):
        super().__init__(parent)
        self._is_blocked = False

    @abstractmethod
    def _get_list(self) -> list[_Range]:
        """Get the list of ranges."""

    @abstractmethod
    def update(self, val: list[_Range]) -> None:
        """Set a list of ranges."""

    def __repr__(self) -> str:
        rng_str: list[str] = []
        for rng in self:
            r, c = rng
            rng_str.append(f"[{_fmt_slice(r)}, {_fmt_slice(c)}]")
        return f"{self.__class__.__name__}({', '.join(rng_str)})"

    def __getitem__(self, index: int) -> _Range:
        """The selected range at the given index."""
        return self._get_list()[index]

    def __setitem__(self, index: int, val: _SingleSelection) -> None:
        if self._is_blocked:
            raise RuntimeError("Cannot set item while blocked.")
        lst = self._get_list()
        lst[index] = val
        return self.update(lst)

    def __delitem__(self, index: int) -> None:
        if self._is_blocked:
            raise RuntimeError("Cannot delete item while blocked.")
        lst = self._get_list()
        del lst[index]
        return self.update(lst)

    def __len__(self) -> int:
        """Number of selections."""
        return len(self._get_list())

    def __iter__(self):
        """Iterate over the selection ranges."""
        return iter(self._get_list())

    def _set_value(self, value: SelectionType):
        if self._is_blocked:
            raise RuntimeError("Cannot set item(s) while blocked.")
        if not isinstance(value, list):
            value = [value]
        return self.update(value)

    @property
    def values(self) -> SelectedData:
        return SelectedData(self)

    def insert(self, index: int, rng: _Range) -> None:
        if self._is_blocked:
            raise RuntimeError("Cannot insert item while blocked.")
        lst = self._get_list()
        lst.insert(index, rng)
        return self.update(lst)

    @contextmanager
    def blocked(self, block: bool = True):
        _was_blocked = self._is_blocked
        self._is_blocked = block
        try:
            yield
        finally:
            self._is_blocked = _was_blocked

    def block(self, block: bool = True) -> bool:
        """Block or unblock changing ranges."""
        self._is_blocked = block
        return block


class SelectionRanges(_TableRanges):
    """A table data specific selection range list."""

    def _get_list(self):
        return list(self.parent._qwidget.selections())

    def update(self, value: SelectionRanges):
        """Update the selection ranges."""
        return self.parent._qwidget.setSelections(value)


class HighlightRanges(_TableRanges):
    """A table data specific highlight list."""

    def _get_list(self):
        return list(self.parent._qwidget.highlights())

    def update(self, value: HighlightRanges):
        """Update the highlight ranges."""
        return self.parent._qwidget.setHighlights(value)


class SelectedData(Sequence["pd.DataFrame"]):
    """Interface with the selected data."""

    def __init__(self, obj: SelectionRanges):
        self._obj = obj

    def __getitem__(self, index: int) -> pd.DataFrame:
        """Get the selected data at the given index of selection."""
        data = self._obj.parent.data_shown
        sl = self._obj[index]
        return data.iloc[sl]

    def __len__(self) -> int:
        """Number of selections."""
        return len(self._obj)

    def __iter__(self) -> Iterator[pd.DataFrame]:
        return (self[i] for i in range(len(self)))

    def itercolumns(self) -> Iterator[tuple[Hashable, pd.Series]]:
        all_data: dict[Hashable, pd.Series] = {}
        import pandas as pd

        for data in self:
            for col in data.columns:
                if col in all_data.keys():
                    all_data[col] = pd.concat([all_data[col], data[col]])
                else:
                    all_data[col] = data[col]
        return iter(all_data.items())


class ColumnDtypeInterface(
    Component["SpreadSheet"], MutableMapping[Hashable, "_DtypeLike"]
):
    """Interface to the column dtype of spreadsheet."""

    def __getitem__(self, key: Hashable) -> _DtypeLike | None:
        """Get the dtype of the given column name."""
        return self.parent._qwidget._columns_dtype.get(key, None)

    def __setitem__(self, key: Hashable, dtype: Any) -> None:
        """Set a dtype to the given column name."""
        return self.parent._qwidget.setColumnDtype(key, dtype)

    def __delitem__(self, key: Hashable) -> None:
        """Reset the dtype to the given column name."""
        return self.parent._qwidget.setColumnDtype(key, None)

    def __repr__(self) -> str:
        clsname = type(self).__name__
        dict = self.parent._qwidget._columns_dtype
        return f"{clsname}({dict!r})"

    def __len__(self) -> str:
        return len(self.parent._qwidget._columns_dtype)

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self.parent._qwidget._columns_dtype)

    def set_dtype(
        self,
        name: Hashable,
        dtype: Any,
        *,
        validation: bool = True,
        formatting: bool = True,
    ) -> None:
        """Set dtype and optionally default validator and formatter."""
        self.parent._qwidget.setColumnDtype(name, dtype)
        if validation:
            self.parent._qwidget._set_default_data_validator(name)
        if formatting:
            self.parent._qwidget._set_default_text_formatter(name)
        return None


class CellReferenceInterface(
    _TableComponent, Mapping["tuple[int, int]", InCellRangedSlot]
):
    """Interface to the cell references of a table."""

    def _table_map(self):
        return self.parent._qwidget._qtable_view._table_map

    def __getitem__(self, key: tuple[int, int]):
        return self._table_map()[key]

    def __iter__(self) -> Iterator[InCellRangedSlot]:
        return iter(self._table_map())

    def __len__(self) -> int:
        return len(self._table_map())

    def __repr__(self) -> str:
        slots = self._table_map()
        cname = type(self).__name__
        if len(slots) == 0:
            return f"{cname}()"
        s = ",\n\t".join(f"{k}: {slot!r}" for k, slot in slots.items())
        return f"{cname}(\n\t{s}\n)"


class ProxyInterface(_TableComponent):
    """Interface to the table sorting/filtering."""

    @overload
    def sort(self, by: str | Sequence[str], ascending: bool = True) -> None:
        ...

    @overload
    def sort(self, func: Callable[[pd.DataFrame], _SortArray]) -> None:
        ...

    def sort(self, by, ascending: bool = True) -> None:
        """
        Apply sort proxy to the table.

        If column names are given, sort button(s) will be added to the header.
        """
        if callable(by):
            sort_func = self._get_sort_function(by, ascending)
            return self.parent.proxy.set(sort_func)

        from tabulous._qt._proxy_button import QHeaderSortButton

        if isinstance(by, str):
            by = [by]
        QHeaderSortButton.from_table(self.parent, by, ascending=ascending)
        return None

    def _get_sort_function(
        self,
        by: str | Sequence[str] | Callable[[pd.DataFrame], _SortArray],
        ascending: bool = True,
    ) -> Callable[[pd.DataFrame], _SortArray]:
        if callable(by):
            if not ascending:
                raise TypeError("Cannot sort by a callable in descending order.")

            def _sort(df: pd.DataFrame) -> _SortArray:
                arr = np.asarray(by(df))
                if arr.ndim != 1:
                    raise TypeError("The callable must return a 1D array.")
                elif arr.dtype.kind not in "ui":
                    raise TypeError("The callable must return an integer array.")
                return arr

        else:
            if not isinstance(by, str) and len(by) == 1:
                by = by[0]

            if isinstance(by, str):

                def _sort(df: pd.DataFrame) -> _SortArray:
                    out = np.asarray(df[by].argsort())
                    if not ascending:
                        out = out[::-1]
                    return out

            elif isinstance(by, Sequence):
                by = list(by)

                def _sort(df: pd.DataFrame) -> _SortArray:
                    df_sub = df[by]
                    nr = len(df_sub)
                    df_sub.index = range(nr)
                    df_sub = df_sub.sort_values(by=by, ascending=ascending)
                    return np.asarray(df_sub.index)

            else:
                raise TypeError(
                    "The `by` argument must be a column name or a sequence of it."
                )

            _sort.__name__ = f"sort<by={by!r}, ascending={ascending}>"
        return _sort

    @overload
    def filter(self, expr: str, namespace: dict = {}) -> None:
        ...

    @overload
    def filter(self, func: Callable[[pd.DataFrame], _FilterArray]) -> None:
        ...

    def filter(self, expr: str, namespace: dict = {}) -> None:
        """Apply filter proxy to the table."""
        if callable(expr):
            func = expr
            if namespace:
                raise TypeError("Cannot use a namespace with a callable.")

            def _filter(df: pd.DataFrame) -> _FilterArray:
                arr = np.asarray(func(df))
                if arr.ndim != 1:
                    raise TypeError("The callable must return a 1D array.")
                elif arr.dtype.kind != "b":
                    raise TypeError("The callable must return a boolean array.")
                return arr

        else:

            def _filter(df: pd.DataFrame) -> np.ndarray:
                ns = dict(**dict(df.items()), **namespace)
                return eval(expr, ns, {})

            _filter.__name__ = f"filter<{expr!r}>"

        self.parent._qwidget.setProxy(_filter)
        return None

    def show_filter_button(self, columns: str | list[str]):
        from tabulous._qt._proxy_button import QHeaderFilterButton

        table = self.parent
        if isinstance(columns, str):
            columns = [columns]
        QHeaderFilterButton.from_table(table, columns, show_menu=False)
        return None

    def reset(self) -> None:
        """Reset filter or sort."""
        return self._set_value(None)

    def set(self, proxy: ProxyType) -> None:
        """Set filter or sort."""
        return self._set_value(proxy)

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply the current proxy to the DataFrame."""
        return self._get_proxy_object().apply(df)

    def as_indexer(self) -> np.ndarray:
        """Return the indexer that represents the current proxy."""
        return self._get_proxy_object().as_indexer(self.parent.data)

    @property
    def proxy_type(self):
        """Return the current proxy type."""
        return self._get_proxy_object().proxy_type

    def _set_value(self, value: Any):
        return self.parent._qwidget.setProxy(value)

    def __set__(self, obj: TableBase, value: ProxyType):
        return super().__set__(obj, value)

    def _get_proxy_object(self):
        """Return the current proxy function."""
        return self.parent._qwidget._proxy


def _fmt_slice(sl: slice) -> str:
    s0 = sl.start if sl.start is not None else ""
    s1 = sl.stop if sl.stop is not None else ""
    return f"{s0}:{s1}"


def _normalize_slice(sl: slice, size: int) -> slice:
    start = sl.start
    stop = sl.stop

    if sl.step not in (None, 1):
        raise ValueError("Row slice step must be 1.")

    if start is None:
        start = 0
    elif start < 0:
        start = size + start
    if stop is None:
        stop = size
    elif stop < 0:
        stop = size + stop
    return slice(start, stop)
