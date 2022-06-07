from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable
from functools import partial
import weakref
from psygnal import SignalGroup, Signal

from .keybindings import register_shortcut

from ..types import SelectionRanges, FilterType
from .._protocols import BackendTableProtocol
from .._qt import QTableLayer

if TYPE_CHECKING:
    import pandas as pd


class FilterProperty:
    
    def __init__(self, obj=None):
        self._obj = obj
    
    def __repr__(self) -> str:
        return f"{type(self).__name__} of {self._obj!r}"
        
    def __get__(self, obj: TableLayerBase | None, type=None):
        return self.__class__(obj)
        
    
    def __set__(self, obj: TableLayerBase | None, value: FilterType):
        if obj is None:
            return None
        data = obj.data
        if callable(value):
            # dry run
            try:
                df = data.head(3)
                filt = value(df)
            except Exception as e:
                raise ValueError(
                    f"Dry run failed with filter function {value} due to following error:\n"
                    f"{type(e).__name__}: {e}"
                ) from None
            
        elif value is not None and len(value) != data.shape[0]:
            raise ValueError(f"Shape mismatch between data {data.shape} and input slice {len(value)}.")
        obj._qwidget.setFilter(value)
    
    def __delete__(self, obj: TableLayerBase):
        if isinstance(obj, TableLayerBase):
            obj.filter = None
        raise AttributeError(f"Cannot delete {type(self).__name__}.")
        
    
    def __getitem__(self, key):
        return FilterIndexer(self._obj, key)


class TableSignals(SignalGroup):
    """Signal group for a Table."""
    
    data = Signal(object)
    selections = Signal(object)
    zoom = Signal(float)
    renamed = Signal(str)

class TableLayerBase(ABC):
    """The base class for a table layer."""
    
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
        """Get the SelectionRanges object of current table selection."""
        rngs = SelectionRanges(self._qwidget.selections())
        rngs.changed.connect(self._qwidget.setSelections)
        rngs.events.removed.connect(lambda i, value: self._qwidget.setSelections(rngs))
        return rngs
    
    @selections.setter
    def selections(self, value) -> None:
        self._qwidget.setSelections(value)
    
    filter = FilterProperty()
    
    def bind_key(self, *seq) -> Callable[[TableLayerBase], Any | None]:
        def register(f):
            register_shortcut(seq, self._qwidget, partial(f, self))
        return register

class TableLayer(TableLayerBase):
    def _create_backend(self, data: pd.DataFrame) -> QTableLayer:
        return QTableLayer(data=data)


import operator as op_

class FilterIndexer:
    def __init__(self, layer: TableLayerBase, key: Any):
        if not isinstance(layer, TableLayerBase):
            raise TypeError(f"Cannot create {type(self).__name__} with {type(layer)}.")
        self.layer = layer
        self._key = key
    
    def __repr__(self) -> str:
        return f"<{type(self).__name__} of {self.layer!r} at column {self._key!r}>"
    
    def __eq__(self, other) -> bool:
        fil = BinaryColumnFilter(
            lambda df: op_.eq(df[self._key], other),
            key=self._key,
            repr=f"df[{self._key!r}] == {other!r}",
        )
        self.layer._qwidget.setFilter(fil)


class BinaryColumnFilter:
    def __init__(
        self,
        func: Callable[[pd.DataFrame], pd.Series], 
        key: Any,
        repr: str | None = None,
    ):
        self._func = func
        self._key = key
        self._repr = repr
    
    def __call__(self, df: pd.DataFrame) -> pd.Series:
        series = self._func(df)
        if self._repr is not None:
            series.name = self._repr.format(self._key)
        return series
        