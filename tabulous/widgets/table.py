from __future__ import annotations
from abc import ABC, abstractmethod
from psygnal import SignalGroup, Signal
import pandas as pd

from ..types import SelectionRanges
from .._protocols import BackendTableProtocol
from .._qt import QTableLayer


class TableSignals(SignalGroup):
    data = Signal(object)
    selections = Signal(object)
    zoom = Signal(float)
    name_ = Signal(str)

class TableLayerBase(ABC):
    signals = TableSignals()
    
    def __init__(self, data, name=None, editable: bool = True):
        if not isinstance(data, pd.DataFrame):
            self._data = pd.DataFrame(data)
        else:
            self._data = data
        self._name = str(name)
        self._qwidget = self._create_backend(self._data)
        self._qwidget.setEditability(editable)
        self._qwidget.connectItemChangedSignal(self.signals.data.emit)
        self._qwidget.connectSelectionChangedSignal(self.signals.selections.emit)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}[{self.name}]"
    
    @abstractmethod
    def _create_backend(self, data: pd.DataFrame) -> BackendTableProtocol:
        ...

    @property
    def data(self) -> pd.DataFrame:
        return self._data
    
    @property
    def shape(self) -> tuple[int, int]:
        return self._qwidget.rowCount(), self._qwidget.columnCount()
    
    def refresh(self) -> None:
        self._qwidget.refreshTable()
    
    @property
    def precision(self) -> int:
        return self._qwidget.precision()
    
    @precision.setter
    def precision(self, value: int) -> None:
        self._qwidget.setPrecision(value)
    
    @property
    def zoom(self) -> float:
        return self._qwidget.zoom()
    
    @zoom.setter
    def zoom(self, value: float):
        self._qwidget.setZoom(value)

    # TODO: connect name signal
    @property
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, value: str):
        self._name = str(value)
        # self.signals.name_.emit(value)

    @property
    def editable(self) -> bool:
        return self._qwidget.editability()
    
    @editable.setter
    def editable(self, value: bool):
        self._qwidget.setEditability(value)
    
    @property
    def columns(self):
        return self._data.columns
    
    @property
    def index(self):
        return self._data.index
    
    @property
    def selections(self):
        rngs = SelectionRanges(self._qwidget.selections())
        rngs.updated.connect(self._qwidget.setSelections)
        rngs.events.removed.connect(lambda i, value: self._qwidget.setSelections(rngs))
        return rngs
    
    @selections.setter
    def selections(self, value) -> None:
        self._qwidget.setSelections(value)


class TableLayer(TableLayerBase):
    def _create_backend(self, data: pd.DataFrame) -> QTableLayer:
        return QTableLayer(data=data)