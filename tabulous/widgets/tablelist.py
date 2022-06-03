from __future__ import annotations
import re
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

    def insert(self, index: int, table: TableLayer):
        if not isinstance(table, TableLayer):
            raise TypeError(f"Cannot insert {type(table)} to {self.__class__.__name__}.")
        
        table.name = self._coerce_name(table.name, except_for=table)
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
        table = self[index_or_name]
        name = self._coerce_name(name, except_for=table)
        table.name = name
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

    def _coerce_name(self, name: str, except_for: TableLayer):
        names = set(content.name for content in self if content is not except_for)
        
        suffix = re.findall(".*-(\d+)", name)
        if suffix:
            suf = suffix[0]
            new_name = name
            name = new_name.rstrip(suf)[:-1]
            i = int(suffix[0])
        else:
            new_name = name
            i = 0
        while new_name in names:
            new_name = f"{name}-{i}"
            i += 1
            
        return new_name