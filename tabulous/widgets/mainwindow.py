from __future__ import annotations
from typing import Any, Callable, NamedTuple, TYPE_CHECKING
from psygnal import SignalGroup, Signal
import numpy as np
import pandas as pd

from .._qt import QMainWindow

from .table import TableLayer
from .tablist import TabList

class MainWindow:
    def __init__(self):
        self._qwidget = QMainWindow()
        self._tablist = TabList(parent=self)
    
    @property
    def tabs(self) -> TabList:
        return self._tablist
    
    def show(self):
        self._qwidget.show()
    
    def add_data(self, data, *, name: str = None, editable: bool = False):
        table = TableLayer(data, name=name, editable=editable)
        self.tabs.append(table)