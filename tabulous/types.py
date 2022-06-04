from __future__ import annotations
from typing import Any, Iterable, TYPE_CHECKING, NewType
from psygnal import Signal
from psygnal.containers import EventedList
import pandas as pd

# class DataFrameType(Protocol):
#     iloc: 

TableData = NewType("TableData", pd.DataFrame)
TableColumn = NewType("Series", pd.Series)

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
    updated = Signal(object)
    
    def __init__(self, ranges: Iterable[tuple[slice, slice]] = ()):
        super().__init__(ranges)
    
    def _pre_insert(self, value):
        _check_tuple_of_slices(value)
        return value
    
    def _post_insert(self, value) -> None:
        self.updated.emit(self)
        return value
