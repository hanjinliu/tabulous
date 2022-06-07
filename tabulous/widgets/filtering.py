from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable

from ..types import FilterType

if TYPE_CHECKING:
    from .table import TableLayerBase
    import pandas as pd

class FilterProperty:
    
    def __init__(self, obj: TableLayerBase | None = None):
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
    
    def get_filter(self):
        return self._obj._qwidget.filter()



import operator as op

class FilterIndexer:
    def __init__(self, layer: TableLayerBase, key: Any):
        if not isinstance(layer, TableLayerBase):
            raise TypeError(f"Cannot create {type(self).__name__} with {type(layer)}.")
        self.layer = layer
        self._key = key
    
    def __repr__(self) -> str:
        return f"<{type(self).__name__} of {self.layer!r} at column {self._key!r}>"
    
    def __eq__(self, other) -> None:
        fil = BinaryColumnFilter.from_operator("__eq__", self._key, other)
        self.layer._qwidget.setFilter(fil)
    
    def __gt__(self, other) -> None:
        fil = BinaryColumnFilter.from_operator("__gt__", self._key, other)
        self.layer._qwidget.setFilter(fil)
    
    def __ge__(self, other) -> None:
        fil = BinaryColumnFilter.from_operator("__ge__", self._key, other)
        self.layer._qwidget.setFilter(fil)

    def __lt__(self, other) -> None:
        fil = BinaryColumnFilter.from_operator("__lt__", self._key, other)
        self.layer._qwidget.setFilter(fil)
    
    def __le__(self, other) -> None:
        fil = BinaryColumnFilter.from_operator("__ge__", self._key, other)
        self.layer._qwidget.setFilter(fil)

    def __ne__(self, other) -> None:
        fil = BinaryColumnFilter.from_operator("__ne__", self._key, other)
        self.layer._qwidget.setFilter(fil)
    
    def between(self, low, high) -> None:
        fil = BinaryColumnFilter(
            lambda df: (low < df[self._key]) & (df[self._key] < high),
            repr=f"{low!r} < df[{self._key!r}] < {high!r}",
        )
        self.layer._qwidget.setFilter(fil)

class BinaryColumnFilter:
    def __init__(
        self,
        func: Callable[[pd.DataFrame], pd.Series], 
        repr: str | None = None,
    ):
        self._func = func
        self._repr = repr
    
    def __call__(self, df: pd.DataFrame) -> pd.Series:
        series = self._func(df)
        if self._repr is not None:
            series.name = self._repr
        return series
    
    @classmethod
    def from_operator(self, op_func, key, other):
        f = getattr(op, op_func)
        return BinaryColumnFilter(
            lambda df: f(df[key], other),
            repr=f"df[{key!r}] == {other!r}",
        )

OPERATORS = {
    "__eq__": "==",
    "__gt__": ">",
    "__ge__": ">=",
    "__lt__": "<",
    "__le__": "<=",
    "__ne__": "!=",
}