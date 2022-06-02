from __future__ import annotations
from typing import Any, Callable, NamedTuple, TYPE_CHECKING
from psygnal import SignalGroup, Signal
from psygnal.containers import EventedList
import numpy as np
import pandas as pd

from .table import TableLayer

if TYPE_CHECKING:
    from .mainwindow import TableViewer

class TableList(EventedList[TableLayer]):
    def __init__(self, parent: TableViewer):
        super().__init__()
        self._parent = parent
        self.events.inserted.connect(self._on_inserted)
        self.events.removed.connect(self._on_removed)

    def insert(self, index: int, table: TableLayer):
        if not isinstance(table, TableLayer):
            raise TypeError(f"Cannot insert {type(table)} to {self.__class__.__name__}.")
        
        table.name = self._coerce_name(table.name)
        super().insert(index, table)
    
    def index(self, value: TableLayer | str, start: int = 0, stop: int = 999999) -> int:
        """Override of list.index(), also accepts str input."""
        if isinstance(value, str):
            for i, content in enumerate(self):
                if content.name == value:
                    return i
            else:
                raise ValueError(f"No table named {value}")
        else:
            return super().index(value, start, stop)
    
    def rename(self, index_or_name: int | str, name: str) -> None:
        if isinstance(index_or_name, int):
            index = index_or_name
        elif isinstance(index_or_name, str):
            index = self.index(index_or_name)
        else:
            raise TypeError(f"{type(index_or_name)} is not a table specifier.")
        name = self._coerce_name(name)
        self._parent._qwidget.renameTable(index, name)
        return None
    
    def get(self, name: str, default: Any | None = None) -> TableLayer | None:
        for content in self:
            if content.name == name:
                return content
        else:
            return default
    
    def __getitem__(self, key):
        if isinstance(key, str):
            for content in self:
                if content.name == key:
                    return content
            else:
                raise ValueError(f"No table named {key!r}.")
        return super().__getitem__(key)
            
    def _on_inserted(self, index: int):
        table = self[index]
        self._parent._qwidget.addTable(table._qwidget, table.name)
        
    def _on_removed(self, index: int, table: TableLayer):
        del self[index]
        self._parent._qwidget.removeTable(index)

    def _coerce_name(self, name: str):
        names = set(content.name for content in self)
        new_name = name
        i = 0
        while new_name in names:
            new_name = f"{name}-{i}"
            i += 1
            
        return new_name