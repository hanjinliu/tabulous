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
from tabulous.types import _SingleSelection, SelectionType, EvalInfo
from tabulous._eval import Graph

if TYPE_CHECKING:
    from typing_extensions import Self
    import pandas as pd
    from pandas.core.dtypes.dtypes import ExtensionDtype
    from tabulous.widgets._table import TableBase, SpreadSheet
    from tabulous._qt._table._base._header_view import QDataFrameHeaderView

    _DtypeLike = Union[np.dtype, ExtensionDtype]

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


class VerticalHeaderInterface(Component["TableBase"]):
    """The interface for the vertical header of the tablelist."""

    def _get_index(self) -> pd.Index:
        return self.parent._qwidget.model().df.index

    def __getitem__(self, key: int | slice):
        return self._get_index()[key]

    def __setitem__(self, key: int | slice, value: Any):
        table = self.parent
        if not table.editable:
            raise TableImmutableError("Table is not editable.")
        qtable = table._qwidget
        df = table._qwidget.model().df
        if isinstance(key, slice):
            start, stop, step = key.indices(len(df.index))
            for i, idx in enumerate(range(start, stop, step)):
                qtable.setVerticalHeaderValue(idx, value[i])
        else:
            idx = key.__index__()
            qtable.setVerticalHeaderValue(idx, value)
        return None

    def __len__(self) -> int:
        return len(self._get_index())

    def __iter__(self) -> Iterator[str]:
        return iter(self._get_index())

    def get_loc(self, key: str) -> int:
        """Get the location of a column."""
        return self._get_index().get_loc(key)

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

    def _get_header(self) -> QDataFrameHeaderView:
        return self.parent._qwidget._qtable_view.verticalHeader()


class HorizontalHeaderInterface(Component["TableBase"]):
    """The interface for the horizontal header of the tablelist."""

    def _get_columns(self) -> pd.Index:
        return self.parent._qwidget.model().df.columns

    def __getitem__(self, key: int | slice):
        return self._get_columns()[key]

    def __setitem__(self, key: int | slice, value: Any):
        table = self.parent
        if not table.editable:
            raise TableImmutableError("Table is not editable.")
        qtable = table._qwidget
        df = table._qwidget.model().df
        if isinstance(key, slice):
            start, stop, step = key.indices(len(df.index))
            for i, idx in enumerate(range(start, stop, step)):
                qtable.setHorizontalHeaderValue(idx, value[i])
        else:
            idx = key.__index__()
            qtable.setHorizontalHeaderValue(idx, value)
        return None

    def __len__(self) -> int:
        """Number of columns."""
        return len(self._get_columns())

    def __iter__(self) -> Iterator[str]:
        return iter(self._get_columns())

    def get_loc(self, key: str) -> int:
        """Get the location of a column."""
        return self._get_columns().get_loc(key)

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

    def _get_header(self) -> QDataFrameHeaderView:
        return self.parent._qwidget._qtable_view.horizontalHeader()


class CellInterface(Component["TableBase"]):
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
                return table._qwidget._set_widget_at_index(*key, value)
            raise TypeError("Cannot set widget at slices.")

        import pandas as pd
        from .._qt._table._base._line_edit import QCellLiteralEdit

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
        _row_is_slice = isinstance(row, slice)
        _col_is_slice = isinstance(col, slice)
        if _row_is_slice:
            row = slice(*row.indices(self.parent.table_shape[0]))
            if row.step != 1:
                raise ValueError("Row slice step must be 1.")
        else:
            row = slice(row, row + 1)
        if _col_is_slice:
            col = slice(*col.indices(self.parent.table_shape[1]))
            if col.step != 1:
                raise ValueError("Column slice step must be 1.")
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
        table = self.parent._qwidget
        if isinstance(val, str):
            return table.registerAction(val)
        elif callable(val):
            location = val.__name__.replace("_", " ")
            return table.registerAction(location)(val)
        else:
            raise ValueError("input must be a string or callable.")

    def get_label(self, r: int, c: int) -> str | None:
        """Get the label of a cell."""
        return self.parent._qwidget.itemLabel(r, c)

    def set_label(self, r: int, c: int, text: str):
        """Set the label of a cell."""
        return self.parent._qwidget.setItemLabel(r, c, text)

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


class PlotInterface(Component["TableBase"]):
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
        if table._qwidget._qtable_view.parentViewer()._white_background:
            style = None
        else:
            style = "dark_background"
        wdt = QtMplPlotCanvas(nrows=nrows, ncols=ncols, style=style)
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

    def plot(self, *args, **kwargs):
        """Call ``plt.plot`` on the current side figure."""
        out = self.gca().plot(*args, **kwargs)
        self.draw()
        return out

    def scatter(self, *args, **kwargs):
        """Call ``plt.scatter`` on the current side figure."""
        out = self.gca().scatter(*args, **kwargs)
        self.draw()
        return out

    def hist(self, *args, **kwargs):
        """Call ``plt.hist`` on the current side figure."""
        out = self.gca().hist(*args, **kwargs)
        self.draw()
        return out

    def draw(self):
        """Update the current side figure."""
        return self._current_widget.draw()


_Range = Tuple[slice, slice]


class _TableRanges(Component["TableBase"], MutableSequence[_Range]):
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
            rng_str.append(f"[{r.start}:{r.stop}, {c.start}:{c.stop}]")
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

    def update(self, value: SelectionRanges):
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


class CellReferenceInterface(Component["TableBase"], Mapping["tuple[int, int]", Graph]):
    """Interface to the cell references of a table."""

    def _ref_graphs(self):
        return self.parent._qwidget._qtable_view._ref_graphs

    def __getitem__(self, key: tuple[int, int]):
        return self._ref_graphs()[key]

    def __iter__(self) -> Iterator[Graph]:
        return iter(self._ref_graphs())

    def __len__(self) -> int:
        return len(self._ref_graphs())

    def __repr__(self) -> str:
        graphs = self._ref_graphs()
        cname = type(self).__name__
        if len(graphs) == 0:
            return f"{cname}()"
        s = ",\n\t".join(f"{k}: {graph!r}" for k, graph in graphs.items())
        return f"{cname}(\n\t{s}\n)"
