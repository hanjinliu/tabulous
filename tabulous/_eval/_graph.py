from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, MutableMapping
import weakref
from contextlib import contextmanager
import logging

import numpy as np

from tabulous._eval._literal import LiteralCallable, EvalResult

from tabulous._range import RectRange, NoRange, AnyRange
from tabulous._selection_op import SelectionOperator
from tabulous._selection_model import Index

if TYPE_CHECKING:
    from ..widgets import TableBase

logger = logging.getLogger("tabulous")


class Graph:
    """Calculation graph object that works in a table."""

    def __init__(
        self,
        table: TableBase,
        func: LiteralCallable,
        sources: list[SelectionOperator],
    ):
        self._sources = sources
        self._func = func
        self._table_ref = weakref.ref(table)
        self._callback_blocked = False

    def __hash__(self) -> int:
        return id(self)

    def __repr__(self) -> str:
        return f"Graph<{self.expr}>"

    @property
    def expr(self) -> str:
        """Get the graph expression in 'df.iloc[...] = ...' format."""
        if self._func.last_destination is None:
            expr = f"out = {self._func.expr}"
        else:
            rsl, csl = self._func.last_destination
            _r = _format_slice(rsl)
            _c = _format_slice(csl)
            expr = f"df.iloc[{_r}, {_c}] = {self._func.expr}"
        return expr

    @property
    def table(self) -> TableBase | None:
        """The parent table widget."""
        return self._table_ref()

    def set_pos(self, pos: tuple[int, int]):
        """Set the position of the graph origin."""
        self._func.set_pos(pos)
        return self

    @contextmanager
    def blocked(self):
        """Block the callback temporarily."""
        was_blocked = self._callback_blocked
        self._callback_blocked = True
        try:
            yield
        finally:
            self._callback_blocked = was_blocked

    def update(self) -> EvalResult:
        """
        Run the graph and update the destination.

        This function will NOT raise an Exception. Instead, it will return an
        EvalResult object and the error is wrapped inside it.
        """
        table = self.table
        if table is None:
            # garbage collected
            return self.disconnect()

        if not self._callback_blocked:
            with self.blocked():
                out = self._func()
                if out.get_err() and (sl := self._func.last_destination):
                    import pandas as pd

                    rsl, csl = sl
                    # determine the error object
                    if table.table_type == "SpreadSheet":
                        err_repr = "#ERROR"
                    else:
                        err_repr = pd.NA
                    val = np.full(
                        (rsl.stop - rsl.start, csl.stop - csl.start),
                        err_repr,
                        dtype=object,
                    )
                    qtable_view = self.table._qwidget._qtable_view
                    with qtable_view._selection_model.blocked(), qtable_view._ref_graphs.blocked(), table.events.data.blocked():
                        table._qwidget.setDataFrameValue(rsl, csl, pd.DataFrame(val))

            logger.debug(f"Called: {self.expr}, result: {out._short_repr()}")
        else:
            out = EvalResult(None, self._func._pos)
        return out

    def initialize(self):
        """Initialize the graph object."""
        # First exception should be considered as a wrong expression.
        # Disconnect the callback.
        out = self.update()
        if e := out.get_err():
            self.disconnect()
            raise e
        return self

    def connect(self):
        """Connect the graph to the table data-changed event."""
        self.table.events.data.connect(self.update)
        logger.debug(f"Graph connected: {self.expr}")
        return self

    def disconnect(self):
        """Disconnect the graph from the table data-changed event."""
        self.table.events.data.disconnect(self.update)
        logger.debug(f"Graph disconnected: {self.expr}")
        return self


_ANY_RANGE = AnyRange()
_NO_RANGE = NoRange()


class GraphManager(MutableMapping[Index, Graph]):
    """Calculation graph manager."""

    def __init__(self):
        self._graphs: dict[Index, Graph] = {}
        self._update_blocked = False
        self._blocked_ranges: RectRange = _NO_RANGE
        self._to_be_shown: weakref.WeakSet[Graph] = weakref.WeakSet()

    def __getitem__(self, key: Index) -> Graph:
        return self._graphs[key]

    def __setitem__(self, key: Index, graph: Graph) -> None:
        if key not in self._blocked_ranges:
            self.setitem_force(key, graph)

    def setitem_force(self, key: Index, graph: Graph) -> None:
        index = Index(*key)
        self.pop_force(index, None)
        graph.connect()
        graph.initialize()
        self._graphs[index] = graph
        logger.debug(f"Graph added at {key}")
        return None

    def __delitem__(self, key: Index) -> None:
        if key not in self._blocked_ranges:
            self.pop_force(key)

    __void = object()

    def pop_force(self, key: Index, default=__void) -> Graph:
        try:
            graph = self[key]
        except KeyError:
            if default is self.__void:
                raise
            return default
        else:
            graph.disconnect()
            del self._graphs[key]
            logger.debug(f"Graph popped at {key}")
            return graph

    def __len__(self) -> int:
        return len(self._graphs)

    def __iter__(self):
        return iter(self._graphs)

    def is_all_blocked(self) -> bool:
        """True if manager update is disabled at any positions."""
        return self._blocked_ranges is _ANY_RANGE

    @contextmanager
    def blocked(self, *ranges):
        """Block graph updates in the given ranges temporarily."""
        old_range = self._blocked_ranges
        if len(ranges) == 0:
            ranges = _ANY_RANGE
        elif len(ranges) == 2:
            rsl, csl = ranges
            if isinstance(rsl, int):
                rsl = slice(rsl, rsl + 1)
            if isinstance(csl, int):
                csl = slice(csl, csl + 1)
            ranges = RectRange(rsl, csl)
        else:
            raise ValueError
        self._blocked_ranges = ranges
        try:
            yield
        finally:
            self._blocked_ranges = old_range

    def set_to_be_shown(self, graphs: Iterable[Graph]):
        """Set graphs to be shown."""
        return self._to_be_shown.update(graphs)

    def delete_to_be_shown(self, graphs: Iterable[Graph]):
        """Delete graphs to be shown."""
        return self._to_be_shown.difference_update(graphs)

    def insert_rows(self, row: int, count: int):
        """Insert rows and update indices."""
        new_dict = {}
        for idx in list(self._graphs.keys()):
            if idx.row >= row:
                new_idx = Index(idx.row + count, idx.column)
                graph = self._graphs.pop(idx)
                new_dict[new_idx] = graph
                graph.set_pos(new_idx)

        self._graphs.update(new_dict)
        return None

    def insert_columns(self, col: int, count: int):
        """Insert columns and update indices."""
        new_dict = {}
        for idx in list(self._graphs.keys()):
            if idx.column >= col:
                new_idx = Index(idx.row, idx.column + count)
                graph = self._graphs.pop(idx)
                new_dict[new_idx] = graph
                graph.set_pos(new_idx)

        self._graphs.update(new_dict)
        return None

    def remove_rows(self, row: int, count: int):
        """Remove items that are in the given row range."""
        start = row
        stop = row + count
        for idx in list(self._graphs.keys()):
            if start <= idx.row < stop:
                self.pop(idx)
            elif idx.row >= stop:
                new_idx = Index(idx.row - count, idx.column)
                graph = self._graphs.pop(idx)
                self._graphs[new_idx] = graph
                graph.set_pos(new_idx)

        return None

    def remove_columns(self, col: int, count: int):
        """Remove items that are in the given column range."""
        start = col
        stop = col + count
        for idx in list(self._graphs.keys()):
            if start <= idx.column < stop:
                self.pop(idx)
            elif idx.column >= stop:
                new_idx = Index(idx.row, idx.column - count)
                graph = self._graphs.pop(idx)
                self._graphs[new_idx] = graph
                graph.set_pos(new_idx)

        return None


def _format_slice(sl: slice) -> str:
    if sl == slice(None):
        return ":"
    return f"{sl.start}:{sl.stop}"
