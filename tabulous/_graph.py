from __future__ import annotations
from typing import Callable, Any, TYPE_CHECKING
import weakref
from .widgets import TableBase

if TYPE_CHECKING:
    import pandas as pd


class Graph:
    """Calculation graph object that works in a table."""

    def __init__(
        self,
        table: TableBase,
        func: Callable[[], Any],
        sources: list[tuple[slice, slice]],
    ):
        self._sources = sources
        self._func = func
        self._table_ref = weakref.ref(table)

    @property
    def table(self) -> TableBase:
        return self._table_ref()

    def update(self):
        """Update the graph."""
        table = self.table
        print("update", table)
        if table is None:
            self.disconnect()
        else:
            self._func()

    def connect(self):
        self.table.events.data.connect(self.update)
        return None

    def disconnect(self):
        self.table.events.data.disconnect(self.update)
        return None
