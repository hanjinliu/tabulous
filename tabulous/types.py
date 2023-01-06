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
    Mapping,
    MutableSequence,
)
from enum import Enum

import numpy as np
from numpy.typing import ArrayLike, NDArray

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


_IntArray = NDArray[np.integer]
_BoolArray = NDArray[np.bool_]
_IntOrBoolArray = Union[_IntArray, _BoolArray]
ProxyType = Union[Callable[["pd.DataFrame"], _IntOrBoolArray], _IntOrBoolArray]


class TabPosition(Enum):
    """Enum for tab position."""

    top = "top"
    left = "left"
    bottom = "bottom"
    right = "right"


class _InfoVar:
    def __init__(self, name: str) -> None:
        self._name = name

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
    DELETED = _InfoVar("DELETED")
    INSERTED = _InfoVar("INSERTED")

    row: int | slice
    column: int | slice
    value: Any
    old_value: Any

    @property
    def col(self) -> int | slice:
        """Alias of `column`."""
        return self.column


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

    pos : tuple[int, int]
        The visual position of the cell where expression is evaluated.
    source_pos : tuple[int, int]
        The source position of the cell where expression is evaluated.
    expr : str
        Expression to be evaluated.
    is_ref: bool
        Whether the expression take references in the table.
    """

    pos: tuple[int, int]
    source_pos: tuple[int, int]
    expr: str
    is_ref: bool

    @property
    def col(self) -> int:
        """Alias of `column`."""
        return self.column


_Sliceable = Union[SupportsIndex, slice]
_SingleSelection = Tuple[_Sliceable, _Sliceable]
SelectionType = List[_SingleSelection]


def __getattr__(name: str) -> Any:
    if name == "FilterType":
        import warnings

        warnings.warn(
            "'FilterType 'is deprecated. Please use 'ProxyType' instead.",
            DeprecationWarning,
        )
        return ProxyType
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


ColorType = Union[str, Iterable[int]]
ColorMapping = Union[Callable[[Any], ColorType], Mapping[str, ColorType]]
