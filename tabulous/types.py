from __future__ import annotations
from typing import Any, Callable, Iterable, NewType, Annotated, Tuple, List, Union, TYPE_CHECKING
from enum import Enum
from psygnal import Signal
from psygnal.containers import EventedList

import numpy as np
from numpy.typing import ArrayLike

if TYPE_CHECKING:
    import pandas as pd
    _TableLike = Union[pd.DataFrame, dict, Iterable, ArrayLike]
else:
    _TableLike = Any

# class DataFrameType(Protocol):
#     iloc: 

__all__ = [
    "TableData",
    "TableColumn",
    "TableDataTuple",
    "TableInfo",
    "SelectionRanges",
]

if TYPE_CHECKING:
    TableData = NewType("TableData", pd.DataFrame)
    TableColumn = NewType("TableColumn", pd.Series)
else:
    TableData = NewType("TableData", Any)
    TableColumn = NewType("TableColumn", Any)

TableDataTuple = NewType("TableDataTuple", tuple)

class TableInfoAlias(type):    
    def __getitem__(cls, names: str | tuple[str, ...]):
        if isinstance(names, str):
            names = (names,)
        else:
            for name in names:
                if not isinstance(name, str):
                    raise ValueError(f"Cannot subscribe type {type(name)} to TableInfo.")
        
        return Annotated[TableInfoInstance, {"column_choice_names": names}]

class TableInfo(metaclass=TableInfoAlias):
    def __new__(cls, *args, **kwargs):
        raise TypeError(f"Type {cls.__name__} cannot be instantiated.")

class TableInfoInstance(Tuple["pd.DataFrame", List[str]]):
    def __new__(cls, *args, **kwargs):
        raise TypeError(f"Type {cls.__name__} cannot be instantiated.")

def _check_tuple_of_slices(value: Any) -> tuple[slice, slice]:
    v0, v1 = value
    if isinstance(v0, slice) and isinstance(v1, slice):
        if v0.step and v0.step != 1:
            raise ValueError("Cannot set slice with step.")
        if v1.step and v1.step != 1:
            raise ValueError("Cannot set slice with step.")
        return tuple(value)
    else:
        raise TypeError(f"Invalid input: ({type(v0)}, {type(v1)}).")

class SelectionRanges(EventedList[tuple[slice, slice]]):
    """A table data specific selection range list."""
    
    _changed = Signal(object)
    
    def __init__(self, ranges: Iterable[tuple[slice, slice]] = ()):
        super().__init__(ranges)
    
    def _pre_insert(self, value):
        _check_tuple_of_slices(value)
        return value
    
    def _post_insert(self, value) -> None:
        self._changed.emit(self)
        return value

FilterType = Union[Callable[["pd.DataFrame"], np.ndarray], np.ndarray]

class TabPosition(Enum):
    top = "top"
    left = "left"
    bottom = "bottom"
    right = "right"
