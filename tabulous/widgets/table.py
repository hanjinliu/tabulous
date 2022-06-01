from __future__ import annotations
from typing import Any, Callable, NamedTuple, TYPE_CHECKING
from psygnal import SignalGroup, Signal
import numpy as np
import pandas as pd

from .._qt import QTableLayer


class TableSignals(SignalGroup):
    data = Signal(object)
    selection = Signal(object)
    

class TableLayer:
    signals = TableSignals()
    
    def __init__(self, data, name=None, editable: bool = True):
        self._data = pd.DataFrame(data)
        self._name = name
        self._qwidget = QTableLayer(data=self._data)
        self._qwidget.setEditability(editable)
        self._qwidget.itemChangedSignal.connect(self.signals.data.emit)
    
    @property
    def data(self) -> pd.DataFrame:
        return self._data
    
    @property
    def shape(self) -> tuple[int, int]:
        return self._qwidget.rowCount(), self._qwidget.columnCount()

    @property
    def name(self) -> str:
        return str(self._name)

    @property
    def editable(self) -> bool:
        return self._qwidget.editability()
    
    @editable.setter
    def editable(self, value: bool):
        self._qwidget.setEditability(value)