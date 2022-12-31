from __future__ import annotations
from typing import Mapping, TypeVar, Iterator, Tuple
from tabulous._psygnal import InCellRangedSlot
from ._base import TableComponent


T = TypeVar("T")


class CellReferenceInterface(
    TableComponent, Mapping[Tuple[int, int], InCellRangedSlot]
):
    """Interface to the cell references of a table."""

    def _table_map(self):
        return self.parent._qwidget._qtable_view._table_map

    def __getitem__(self, key: tuple[int, int]):
        return self._table_map()[key]

    def __iter__(self) -> Iterator[InCellRangedSlot]:
        return iter(self._table_map())

    def __len__(self) -> int:
        return len(self._table_map())

    def __repr__(self) -> str:
        slots = self._table_map()
        cname = type(self).__name__
        if len(slots) == 0:
            return f"{cname}()"
        s = ",\n\t".join(f"{k}: {slot!r}" for k, slot in slots.items())
        return f"{cname}(\n\t{s}\n)"
