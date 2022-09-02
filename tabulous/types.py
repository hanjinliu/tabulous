from __future__ import annotations
from typing import (
    Any,
    Callable,
    Iterable,
    NewType,
    Tuple,
    List,
    Union,
    TYPE_CHECKING,
    NamedTuple,
    SupportsIndex,
)
from enum import Enum

import numpy as np
from numpy.typing import ArrayLike

if TYPE_CHECKING:
    import pandas as pd
    from .widgets import TableBase

    _TableLike = Union[pd.DataFrame, dict, Iterable, ArrayLike]
else:
    _TableLike = Any


__all__ = [
    "TableData",
    "TableColumn",
    "TableDataTuple",
    "TableInfo",
    "TablePosition",
    "ItemInfo",
    "HeaderInfo",
    "SelectionRanges",
    "SelectionType",
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
        from typing_extensions import Annotated

        if isinstance(names, str):
            names = (names,)
        else:
            for name in names:
                if not isinstance(name, str):
                    raise ValueError(
                        f"Cannot subscribe type {type(name)} to TableInfo."
                    )

        return Annotated[TableInfoInstance, {"column_choice_names": names}]


class TableInfo(metaclass=TableInfoAlias):
    """
    A generic type to describe a DataFrame and its column names.

    ``TableInfo["x", "y"]`` is equivalent to ``tuple[pd.DataFrame, str, str]``
    with additional information for magicgui construction.
    """

    def __new__(cls, *args, **kwargs):
        raise TypeError(f"Type {cls.__name__} cannot be instantiated.")


class TableInfoInstance(Tuple["pd.DataFrame", List[str]]):
    def __new__(cls, *args, **kwargs):
        raise TypeError(f"Type {cls.__name__} cannot be instantiated.")


FilterType = Union[Callable[["pd.DataFrame"], np.ndarray], np.ndarray]


class TabPosition(Enum):
    """Enum for tab position."""

    top = "top"
    left = "left"
    bottom = "bottom"
    right = "right"


class ItemInfo(NamedTuple):
    """
    A named tuple for item update.

    Value takes (row, column, value, old_value) where

    row : int or slice
        Row index or slice where item edited.
    column : int or slice
        Column index or slice where item edited.
    value : Any
        New value of the item.
    old_value : Any
        Old value of the item.
    """

    row: int | slice
    column: int | slice
    value: Any
    old_value: Any


class HeaderInfo(NamedTuple):
    """
    A named tuple for header update.

    Value takes (index, value, old_value) where

    index : int
        Index where item edited.
    value : Any
        New value of the item.
    old_value : Any
        Old value of the item.
    """

    index: int
    value: Any
    old_value: Any


_Sliceable = Union[SupportsIndex, slice]
_SingleSelection = Tuple[_Sliceable, _Sliceable]
SelectionType = List[_SingleSelection]
