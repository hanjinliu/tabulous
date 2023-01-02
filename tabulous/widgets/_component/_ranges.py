from __future__ import annotations
from abc import abstractmethod
from contextlib import contextmanager
from typing import (
    Hashable,
    TYPE_CHECKING,
    MutableSequence,
    Sequence,
    TypeVar,
    Tuple,
    Iterator,
)

from tabulous.types import _SingleSelection, SelectionType
from ._base import TableComponent

if TYPE_CHECKING:
    import pandas as pd


T = TypeVar("T")
_Range = Tuple[slice, slice]


class _TableRanges(TableComponent, MutableSequence[_Range]):
    def __init__(self, parent: T = TableComponent._no_ref):
        super().__init__(parent)
        self._is_blocked = False

    @abstractmethod
    def _get_list(self) -> list[_Range]:
        """Get the list of ranges."""

    @abstractmethod
    def update(self, val: list[_Range]) -> None:
        """Set a list of ranges."""

    def __repr__(self) -> str:
        rng_str: list[str] = []
        for rng in self:
            r, c = rng
            rng_str.append(f"[{_fmt_slice(r)}, {_fmt_slice(c)}]")
        return f"{self.__class__.__name__}({', '.join(rng_str)})"

    def __getitem__(self, index: int) -> _Range:
        """The selected range at the given index."""
        return self._get_list()[index]

    def __setitem__(self, index: int, val: _SingleSelection) -> None:
        if self._is_blocked:
            raise RuntimeError("Cannot set item while blocked.")
        lst = self._get_list()
        lst[index] = val
        return self.update(lst)

    def __delitem__(self, index: int) -> None:
        if self._is_blocked:
            raise RuntimeError("Cannot delete item while blocked.")
        lst = self._get_list()
        del lst[index]
        return self.update(lst)

    def __len__(self) -> int:
        """Number of selections."""
        return len(self._get_list())

    def __iter__(self):
        """Iterate over the selection ranges."""
        return iter(self._get_list())

    def _set_value(self, value: SelectionType):
        if self._is_blocked:
            raise RuntimeError("Cannot set item(s) while blocked.")
        if not isinstance(value, list):
            value = [value]
        return self.update(value)

    @property
    def values(self) -> SelectedData:
        return SelectedData(self)

    def insert(self, index: int, rng: _Range) -> None:
        if self._is_blocked:
            raise RuntimeError("Cannot insert item while blocked.")
        lst = self._get_list()
        lst.insert(index, rng)
        return self.update(lst)

    @contextmanager
    def blocked(self, block: bool = True):
        _was_blocked = self._is_blocked
        self._is_blocked = block
        try:
            yield
        finally:
            self._is_blocked = _was_blocked

    def block(self, block: bool = True) -> bool:
        """Block or unblock changing ranges."""
        self._is_blocked = block
        return block


class SelectionRanges(_TableRanges):
    """A table data specific selection range list."""

    def _get_list(self):
        return list(self.parent._qwidget.selections())

    def update(self, value: SelectionRanges):
        """Update the selection ranges."""
        return self.parent._qwidget.setSelections(value)


class HighlightRanges(_TableRanges):
    """A table data specific highlight list."""

    def _get_list(self):
        return list(self.parent._qwidget.highlights())

    def update(self, value: HighlightRanges):
        """Update the highlight ranges."""
        return self.parent._qwidget.setHighlights(value)


class SelectedData(Sequence["pd.DataFrame"]):
    """Interface with the selected data."""

    def __init__(self, obj: SelectionRanges):
        self._obj = obj

    def __getitem__(self, index: int) -> pd.DataFrame:
        """Get the selected data at the given index of selection."""
        data = self._obj.parent.data_shown
        sl = self._obj[index]
        return data.iloc[sl]

    def __len__(self) -> int:
        """Number of selections."""
        return len(self._obj)

    def __iter__(self) -> Iterator[pd.DataFrame]:
        return (self[i] for i in range(len(self)))

    def itercolumns(self) -> Iterator[tuple[Hashable, pd.Series]]:
        all_data: dict[Hashable, pd.Series] = {}
        import pandas as pd

        for data in self:
            for col in data.columns:
                if col in all_data.keys():
                    all_data[col] = pd.concat([all_data[col], data[col]])
                else:
                    all_data[col] = data[col]
        return iter(all_data.items())


def _fmt_slice(sl: slice) -> str:
    s0 = sl.start if sl.start is not None else ""
    s1 = sl.stop if sl.stop is not None else ""
    return f"{s0}:{s1}"
