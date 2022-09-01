from __future__ import annotations
import weakref
from typing import (
    Generic,
    Hashable,
    Literal,
    TYPE_CHECKING,
    TypeVar,
    overload,
    Any,
    Callable,
    Union,
    MutableMapping,
    Iterator,
)

import numpy as np
from ..exceptions import TableImmutableError

if TYPE_CHECKING:
    from typing_extensions import Self
    from pandas.core.dtypes.dtypes import ExtensionDtype
    from ._table import TableBase, SpreadSheet
    from .._qt._table._base._header_view import QDataFrameHeaderView

    _DtypeLike = Union[np.dtype, ExtensionDtype]

T = TypeVar("T")
_F = TypeVar("_F", bound=Callable)


class _NoRef:
    """No reference."""


class Component(Generic[T]):
    _no_ref = _NoRef()

    def __init__(self, parent: T | _NoRef = _no_ref):
        if parent is self._no_ref:
            self._instances: dict[int, T] = {}
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


class VerticalHeaderInterface(Component["TableBase"]):
    """The interface for the vertical header of the tablelist."""

    def __getitem__(self, key: int | slice):
        return self.parent._qwidget.model().df.index[key]

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
        return len(self.parent.data.index)

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

    def __getitem__(self, key: int | slice):
        return self.parent._qwidget.model().df.columns[key]

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
        return len(self.parent.data.columns)

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
        import pandas as pd

        if isinstance(value, str) or not hasattr(value, "__iter__"):
            _value = [[value]]
        else:
            _value = value
        try:
            df = pd.DataFrame(_value)
        except ValueError:
            raise ValueError(f"Could not convert value {_value!r} to DataFrame.")
        row, col = self._normalize_key(key)

        if 1 in df.shape and (col.stop - col.start, row.stop - row.start) == df.shape:
            # it is natural to set an 1-D array without thinking of the direction.
            df = df.T

        table._qwidget.setDataFrameValue(row, col, df)

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


class PlotInterface(Component["TableBase"]):
    """The interface of plotting."""

    def __init__(self, parent=Component._no_ref):
        super().__init__(parent)
        self._current_widget = None

    def gcf(self):
        """Get current figure."""
        if self._current_widget is None:
            self.new_widget()
        return self._current_widget.figure

    def gca(self):
        """Get current axis."""
        if self._current_widget is None:
            self.new_widget()
        return self._current_widget.ax

    def new_widget(self, nrows=1, ncols=1):
        """Create a new plot widget and add it to the table."""
        from .._qt._plot import QtMplPlotCanvas

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


class ColumnDtypeInterface(
    Component["SpreadSheet"], MutableMapping[Hashable, "_DtypeLike"]
):
    """Interface to the column dtype of spreadsheet."""

    def __getitem__(self, key: Hashable) -> _DtypeLike | None:
        return self.parent._qwidget._columns_dtype.get(key, None)

    def __setitem__(self, key: Hashable, dtype: Any) -> None:
        return self.parent._qwidget.setColumnDtype(key, dtype)

    def __delitem__(self, key: Hashable) -> None:
        return self.parent._qwidget.setColumnDtype(None)

    def __repr__(self) -> str:
        clsname = type(self).__name__
        dict = self.parent._qwidget._columns_dtype
        return f"{clsname}({dict!r})"

    def __len__(self) -> str:
        return len(self.parent._qwidget._columns_dtype)

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self.parent._qwidget._columns_dtype)
