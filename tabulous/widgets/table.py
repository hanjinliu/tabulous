from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable
from functools import partial
from psygnal import SignalGroup, Signal

from .keybindings import register_shortcut

from ..types import SelectionRanges, FilterType
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

class FilterArray:
    def __init__(self, arr, name: str):
        self._arr = arr
        self._name = name
    
    def __array__(self):
        return self._arr

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
        """This function creates a backend widget that follows BackendTableProtocol."""

    @property
    def data(self) -> pd.DataFrame:
        """Table data."""
        return self._data
    
    @data.setter
    def data(self, value):
        import pandas as pd
        if not isinstance(value, pd.DataFrame):
            value = pd.DataFrame(value)
                
        self._data = value
        self._qwidget.updateDataFrame(value)
        self.refresh()
    
    @property
    def shape(self) -> tuple[int, int]:
        """Shape of table."""
        return self._qwidget.rowCount(), self._qwidget.columnCount()
    
    def refresh(self) -> None:
        """Refresh table display."""
        self._qwidget.refreshTable()
    
    @property
    def precision(self) -> int:
        """Precision (displayed digits) of table."""
        return self._qwidget.precision()
    
    @precision.setter
    def precision(self, value: int) -> None:
        self._qwidget.setPrecision(value)
    
    @property
    def zoom(self) -> float:
        """Zoom factor of table."""
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
        rngs.changed.connect(self._qwidget.setSelections)
        rngs.events.removed.connect(lambda i, value: self._qwidget.setSelections(rngs))
        return rngs
    
    @selections.setter
    def selections(self, value) -> None:
        self._qwidget.setSelections(value)
    
    @property
    def filter(self) -> FilterType | None:
        """Table filtering array (a boolean array or a function that returns is)."""
        return self._qwidget.filter()
    
    @filter.setter
    def filter(self, value: FilterType) -> None:
        self._qwidget.setFilter(value)

    
    def bind_key(self, *seq) -> Callable[[TableLayerBase], Any | None]:
        def register(f):
            register_shortcut(seq, self._qwidget, partial(f, self))
        return register

class TableLayer(TableLayerBase):
    def _create_backend(self, data: pd.DataFrame) -> QTableLayer:
        return QTableLayer(data=data)
