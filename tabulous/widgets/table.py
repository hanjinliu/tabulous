from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from psygnal import SignalGroup, Signal

from ..types import SelectionRanges
from .._protocols import BackendTableProtocol
from .._qt import QTableLayer

if TYPE_CHECKING:
    import pandas as pd

class TableSignals(SignalGroup):
    """Signal group for a Table."""
    
    data = Signal(object)
    selections = Signal(object)
    zoom = Signal(float)
    renamed = Signal(str)

class TableLayerBase(ABC):
    def __init__(self, data, name=None, editable: bool = True):
        import pandas as pd
        if not isinstance(data, pd.DataFrame):
            self._data = pd.DataFrame(data)
        else:
            self._data = data
        self.events = TableSignals()
        self._name = str(name)
        self._qwidget = self._create_backend(self._data)
        self._qwidget.setEditability(editable)
        self._qwidget.connectItemChangedSignal(self.events.data.emit)
        self._qwidget.connectSelectionChangedSignal(self.events.selections.emit)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}<{self.name!r}>"
    
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

    def _set_name(self, value: str):
        with self.events.renamed.blocked():
            self.name = value
        
    @property
    def name(self) -> str:
        """Table name."""
        return self._name
    
    @name.setter
    def name(self, value: str):
        self._name = str(value)
        self.events.renamed.emit(self._name)

    @property
    def editable(self) -> bool:
        """Editability of table."""
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
    
    @property
    def filter(self):
        # return self._qwidget
        ...
    
    @filter.setter
    def filter(self, value):
        self._qwidget.setFilter(value)


class TableLayer(TableLayerBase):
    def _create_backend(self, data: pd.DataFrame) -> QTableLayer:
        return QTableLayer(data=data)