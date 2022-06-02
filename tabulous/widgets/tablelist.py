from __future__ import annotations
from typing import Any, Callable, NamedTuple, TYPE_CHECKING
from psygnal import SignalGroup, Signal
from psygnal.containers import EventedList
import numpy as np
import pandas as pd

from .table import TableLayer

if TYPE_CHECKING:
    from .mainwindow import MainWindow

class TableList(EventedList[TableLayer]):
    def __init__(self, parent: MainWindow):
        super().__init__()
        self._parent = parent
        self.events.inserted.connect(self._on_inserted)
        self.events.removed.connect(self._on_removed)

    def insert(self, index: int, table: TableLayer):
        if not isinstance(table, TableLayer):
            raise TypeError(f"Cannot insert {type(table)} to {self.__class__.__name__}.")
        super().insert(index, table)
    
    def rename(self, index: int, name: str):
        self._parent._qwidget.renameTable(index, name)
    
    def __getitem__(self, key):
        if isinstance(key, str):
            for content in self:
                if content.name == key:
                    return key
            else:
                raise ValueError(f"No table named {key!r}.")
        return super().__getitem__(key)
    
    def _on_inserted(self, index):
        table = self[index]
        self._parent._qwidget.addTable(table._qwidget, table.name)
        
    def _on_removed(self, index: int, table: TableLayer):
        del self[index]
        self._parent._qwidget.removeTable(index)