from __future__ import annotations
from pathlib import Path
from typing import Any, Callable, NamedTuple, TYPE_CHECKING
from psygnal import SignalGroup, Signal
import numpy as np
import pandas as pd

from .._qt import QMainWindow, get_app

from .table import TableLayer
from .tablelist import TableList

class TableViewer:
    
    def __init__(self, *, show: bool = True):
        app = get_app()
        self._qwidget = QMainWindow()
        self._qwidget._table_viewer = self
        self._tablist = TableList(parent=self)
        if show:
            self.show()
    
    @property
    def tables(self) -> TableList:
        return self._tablist
    
    def show(self):
        self._qwidget.show()
    
    def add_data(self, data, *, name: str = None, editable: bool = False):
        table = TableLayer(data, name=name, editable=editable)
        self.tables.append(table)
    
    def read_csv(self, path, *args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        name = Path(path).stem
        self.add_data(df, name=name)
        return df
    
    def read_excel(self, path, *args, **kwargs):
        df_dict = pd.read_excel(path, *args, **kwargs)
        
        for sheet_name, df in df_dict.items():
            self.add_data(df, name=sheet_name)
        return df_dict
