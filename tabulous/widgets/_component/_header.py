from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Sequence,
    TypeVar,
    overload,
    Any,
    Callable,
    Iterator,
)

import numpy as np
from tabulous.exceptions import TableImmutableError
from ._base import TableComponent

if TYPE_CHECKING:
    import pandas as pd
    from tabulous._qt._table._base._header_view import QDataFrameHeaderView

_F = TypeVar("_F", bound=Callable)


class _HeaderInterface(TableComponent):
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
