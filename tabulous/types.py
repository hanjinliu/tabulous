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
    MutableSequence,
)
from enum import Enum

import numpy as np
from numpy.typing import ArrayLike

if TYPE_CHECKING:
    import pandas as pd

    _TableLike = Union[pd.DataFrame, dict, Iterable, ArrayLike]
    from .widgets._component import SelectionRanges
else:
    _TableLike = Any
    SelectionRanges = MutableSequence[Tuple[slice, slice]]


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


class _InfoVar:
    def __init__(self) -> None:
        self._name = None

    def __set_name__(self, owner, name):
        self._name = f"{owner.__name__}.{name}"

    def __repr__(self) -> str:
        return self._name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _InfoVar):
            return self._name == other._name
        return False


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

    If a row or column is deleted, the value is set to ``DELETED``.
    If a row or column is inserted, the old_value is set to ``INSERTED``.
    """

    # class variables
    DELETED = _InfoVar()
    INSERTED = _InfoVar()

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


class EvalInfo(NamedTuple):
    """
    A named tuple for evaluation.

    Value takes (row, column, expr, old_value, is_ref) where

    row : int
        Row index where item edited.
    column : int
        Column index where item edited.
    expr : str
        Expression to be evaluated.
    is_ref: bool
        Whether the expression take references in the table.
    """

    row: int
    column: int
    expr: str
    is_ref: bool


_Sliceable = Union[SupportsIndex, slice]
_SingleSelection = Tuple[_Sliceable, _Sliceable]
SelectionType = List[_SingleSelection]
