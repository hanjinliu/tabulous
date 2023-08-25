from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, overload, Any, Iterator, List

import numpy as np
from psygnal import Signal, SignalGroup
from tabulous.exceptions import TableImmutableError
from tabulous.types import HeaderInfo
from ._base import Component, TableComponent
from tabulous.widgets._registry import SupportActionRegistration

if TYPE_CHECKING:
    import pandas as pd
    from tabulous.widgets import TableBase  # noqa: F401
    from tabulous._qt._table._base._header_view import QDataFrameHeaderView


class HeaderEvents(SignalGroup):
    selected = Signal(List[slice])
    renamed = Signal(HeaderInfo)


class HeaderSectionSpan(Component["_HeaderInterface"]):
    def __getitem__(self, index: int) -> int:
        header = self.parent._get_header()
        return header.sectionSize(index)

    def __setitem__(
        self,
        index: int | slice | list[int],
        span: int | Sequence[int],
    ) -> None:
        header = self.parent._get_header()
        if isinstance(index, (slice, list)):
            if isinstance(index, slice):
                index = list(range(*index.indices(header.count())))
            if isinstance(span, Sequence):
                # set span for each section
                if len(span) != len(index):
                    raise ValueError("Size mismatch between destination and spans.")
                [header.resizeSection(idx, sp) for idx, sp in zip(index, span)]
            else:
                [header.resizeSection(idx, span) for idx in index]
        else:
            header.resizeSection(index, span)

    def __iter__(self) -> Iterator[int]:
        return iter(int(a) for a in self.parent._get_header()._section_sizes)

    def __eq__(self, other: Any) -> bool:
        return np.all(
            self.parent._get_header()._section_sizes.astype(np.uint16) == other
        )

    def resize_to_content(self):
        from qtpy.QtWidgets import QHeaderView

        header = self.parent._get_header()
        header.resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        return None

    def __repr__(self) -> str:
        sizes = self.parent._get_header()._section_sizes
        return f"{type(self).__name__}({sizes.astype(np.uint16).tolist()!r})"


class _HeaderInterface(TableComponent, SupportActionRegistration["TableBase", int]):
    """
    Interface to the table {index/columns} header.

    Similar to pandas.DataFrame.{index/columns}, you can get/set labels.

    >>> print(table.{index/columns}[0])
    >>> table.{index/columns}[0] = 'new_label'

    Use :meth:`selected` to get/set selected ranges.

    >>> table.{index/columns}.selected
    >>> table.{index/columns}.selected = [0, 1, 2]
    >>> table.{index/columns}.selected = [slice(0, 3), slice(6, 8)]

    Use :meth:`insert` / :meth:`remove` to run insert/remove command in
    spreadsheet.

    >>> table.{index/columns}.insert(at=0, count=2)
    >>> table.{index/columns}.remove(at=0, count=2)

    Use ``register`` to register a contextmenu function.

    >>> @table.{index/columns}.register("My Action")
    >>> def my_action(table, index):
    ...     # do something

    Many other pandas.Index methods are also available.

    >>> table.{index/columns}.str.contains('foo')
    >>> table.{index/columns}.isin(['foo', 'bar'])
    >>> table.{index/columns}.get_loc('foo')
    """

    _AXIS_NUMBER: int

    def __init__(self, parent: TableBase = TableComponent._no_ref):
        super().__init__(parent)
        self.events = HeaderEvents()

    def _get_axis(self) -> pd.Index:
        raise NotImplementedError()

    def _set_value(self, idx: int, val: Any):
        raise NotImplementedError()

    def _get_header(self) -> QDataFrameHeaderView:
        raise NotImplementedError()

    @property
    def _qcontextmenu(self):
        """The QContextMenu widget."""
        return self._get_header()._qt_context_menu

    def __repr__(self) -> str:
        return f"<{type(self).__name__}({self._get_axis()!r}) of {self.parent!r}>"

    # fmt: off
    @overload
    def __getitem__(self, key: int) -> str: ...
    @overload
    def __getitem__(self, key: slice | list[int] | np.ndarray) -> Sequence[str]: ...
    # fmt: on

    def __getitem__(self, key):
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
        """The string accessor to the header."""
        return self._get_axis().str

    @property
    def size(self) -> int:
        """Size of the axis."""
        return self._get_axis().size

    @property
    def data(self) -> pd.Index:
        return self._get_axis()

    def get_loc(self, key: str) -> int:
        """Get the location of a label."""
        return self._get_axis().get_loc(key)

    def isin(self, values) -> np.ndarray:
        """Return a boolean array of whether each is found in the passed values."""
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

    def _get_qregistry(self):
        return self._get_header()

    @property
    def selected(self) -> list[slice]:
        """Return the selected ranges."""
        smodel = self.parent._qwidget._qtable_view._selection_model
        out = [
            smodel.ranges[i][self._AXIS_NUMBER] for i in smodel._col_selection_indices
        ]
        return out

    @property
    def span(self) -> HeaderSectionSpan:
        """Sub-field to interact with section spans."""
        return HeaderSectionSpan(self)


class VerticalHeaderInterface(_HeaderInterface):
    __doc__ = _HeaderInterface.__doc__.replace("{index/columns}", "index")
    _AXIS_NUMBER = 0

    def _get_axis(self) -> pd.Index:
        return self.parent._qwidget.model().df.index

    def _set_value(self, idx: int, val: Any):
        return self.parent._qwidget.setVerticalHeaderValue(idx, val)

    def _get_header(self) -> QDataFrameHeaderView:
        return self.parent._qwidget._qtable_view.verticalHeader()

    def insert(self, at: int, count: int = 1):
        """Insert `count` rows at the given position."""
        sheet = self._assert_spreadsheet()
        with sheet._qwidget._anim_row.using_animation(False):
            sheet._qwidget.insertRows(at, count)

    def remove(self, at: int, count: int = 1):
        """Remove `count` rows at the given position."""
        sheet = self._assert_spreadsheet()
        with sheet._qwidget._anim_row.using_animation(False):
            sheet._qwidget.removeRows(at, count)

    @_HeaderInterface.selected.setter
    def selected(self, slices: int | slice | list[int | slice]):
        """Set the selected ranges."""
        if isinstance(slices, (int, slice)):
            slices = [slices]
        smodel = self.parent._qwidget._qtable_view._selection_model
        smodel.clear()
        csl = slice(0, smodel._col_count_getter())
        smodel.extend(
            ((_as_slice(sl), csl) for sl in slices),
            row=True,
        )
        self.parent.refresh()


class HorizontalHeaderInterface(_HeaderInterface):
    __doc__ = _HeaderInterface.__doc__.replace("{index/columns}", "columns")
    _AXIS_NUMBER = 1

    def _get_axis(self) -> pd.Index:
        return self.parent._qwidget.model().df.columns

    def _set_value(self, idx: int, val: Any):
        return self.parent._qwidget.setHorizontalHeaderValue(idx, val)

    def _get_header(self) -> QDataFrameHeaderView:
        return self.parent._qwidget._qtable_view.horizontalHeader()

    def insert(self, at: int, count: int = 1):
        """Insert `count` columns at the given position."""
        sheet = self._assert_spreadsheet()
        with sheet._qwidget._anim_col.using_animation(False):
            sheet._qwidget.insertColumns(at, count)

    def remove(self, at: int, count: int = 1):
        """Remove `count` columns at the given position."""
        sheet = self._assert_spreadsheet()
        with sheet._qwidget._anim_col.using_animation(False):
            sheet._qwidget.removeColumns(at, count)

    @_HeaderInterface.selected.setter
    def selected(self, slices: int | slice | list[int | slice]):
        """Set the selected ranges."""
        if isinstance(slices, (int, slice)):
            slices = [slices]
        smodel = self.parent._qwidget._qtable_view._selection_model
        smodel.clear()
        rsl = slice(0, smodel._row_count_getter())
        smodel.extend(
            ((rsl, _as_slice(sl)) for sl in slices),
            column=True,
        )
        self.parent.refresh()


def _as_slice(x: int | slice) -> slice:
    if isinstance(x, slice):
        return x
    else:
        return slice(x, x + 1)
