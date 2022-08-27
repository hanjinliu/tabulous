from __future__ import annotations
from typing import (
    Any,
    Callable,
    Hashable,
    Iterable,
    Iterator,
    NewType,
    Sequence,
    Tuple,
    List,
    Union,
    TYPE_CHECKING,
    NamedTuple,
    SupportsIndex,
)
from enum import Enum
import weakref

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


class SelectionRanges(Sequence[Tuple[slice, slice]]):
    """A table data specific selection range list."""

    def __init__(self, data: TableBase, ranges: Iterable[tuple[slice, slice]] = ()):
        # NOTE: it's better to use NamedTuple for a rectangular selection but
        # unfortunately DataFrame does not support slicing with NamedTuple.
        self._ranges = list(ranges)
        self._data_ref = weakref.ref(data)

    def __repr__(self) -> str:
        rng_str: list[str] = []
        for rng in self:
            r, c = rng
            rng_str.append(f"[{r.start}:{r.stop}, {c.start}:{c.stop}]")
        return f"{self.__class__.__name__}({', '.join(rng_str)})"

    def __getitem__(self, index: int) -> tuple[slice, slice]:
        """The selected range at the given index."""
        return self._ranges[index]

    def __len__(self) -> int:
        """Number of selections."""
        return len(self._ranges)

    def __iter__(self):
        """Iterate over the selection ranges."""
        return iter(self._ranges)

    @property
    def values(self) -> SelectedData:
        return SelectedData(self)


class SelectedData(Sequence["pd.DataFrame"]):
    """Interface with the selected data."""

    def __init__(self, obj: SelectionRanges):
        self._obj = obj

    def __getitem__(self, index: int) -> pd.DataFrame:
        """Get the selected data at the given index of selection."""
        data = self._obj._data_ref().data_shown
        sl = self._obj[index]
        return data.iloc[sl]

    def __len__(self) -> int:
        """Number of selections."""
        return len(self._obj)

    def __iter__(self) -> Iterator[pd.DataFrame]:
        return (self[i] for i in range(len(self)))

    def itercolumns(self) -> Iterable[tuple[Hashable, pd.Series]]:
        all_data: dict[Hashable, pd.Series] = {}
        for data in self:
            for col in data.columns:
                if col in all_data.keys():
                    all_data[col] = pd.concat([all_data[col], data[col]])
                else:
                    all_data[col] = data[col]
        return iter(all_data.items())


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
