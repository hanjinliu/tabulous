from __future__ import annotations

from contextlib import contextmanager
from typing import (
    Any,
    Iterable,
    Iterator,
    MutableMapping,
    NamedTuple,
    TYPE_CHECKING,
    TypeVar,
)
from psygnal import Signal
import logging
import weakref
from tabulous._range import TableAnchorBase
from tabulous._psygnal import InCellRangedSlot

if TYPE_CHECKING:
    from tabulous.widgets import TableBase


class Index(NamedTuple):
    row: int
    column: int


_V = TypeVar("_V")

logger = logging.getLogger(__name__)


class TableMapping(MutableMapping[Index, _V], TableAnchorBase):
    set = Signal(Index, object)
    deleted = Signal(object)

    def __init__(self) -> None:
        self._dict: dict[Index, _V] = {}

    def __getitem__(self, key: Index) -> _V:
        return self._dict[key]

    def __setitem__(self, key: tuple[int, int], value: _V) -> None:
        logger.debug(f"Setting TableMapping item at {key}")
        index = Index(*key)
        if index in self._dict:
            del self[index]
        self._dict[index] = value
        self.set.emit(key, value)

    def __delitem__(self, key: Index) -> None:
        logger.debug(f"Deleting TableMapping item at {key}")
        value = self._dict.pop(key)
        self.deleted.emit(value)

    def __iter__(self) -> Iterator[Index]:
        return iter(self._dict)

    def __len__(self) -> int:
        return len(self._dict)

    def insert_rows(self, row: int, count: int):
        """Insert rows and update indices."""
        new_dict = {}
        for idx in list(self._dict.keys()):
            if idx.row >= row:
                new_idx = Index(idx.row + count, idx.column)
                child = self._dict.pop(idx)
                new_dict[new_idx] = child
                # if isinstance(child, TableAnchorBase):
                #     child.insert_rows(row, count)

        self._dict.update(new_dict)
        return None

    def insert_columns(self, col: int, count: int):
        """Insert columns and update indices."""
        new_dict = {}
        for idx in list(self._dict.keys()):
            if idx.column >= col:
                new_idx = Index(idx.row, idx.column + count)
                child = self._dict.pop(idx)
                new_dict[new_idx] = child
                # if isinstance(child, TableAnchorBase):
                #     child.insert_columns(col, count)

        self._dict.update(new_dict)
        return None

    def remove_rows(self, row: int, count: int):
        """Remove items that are in the given row range."""
        start = row
        stop = row + count
        for idx in list(self._dict.keys()):
            if start <= idx.row < stop:
                self.pop(idx)
            elif idx.row >= stop:
                new_idx = Index(idx.row - count, idx.column)
                child = self._dict.pop(idx)
                self._dict[new_idx] = child
                # if isinstance(child, TableAnchorBase):
                #     child.remove_rows(row, count)

        return None

    def remove_columns(self, col: int, count: int):
        """Remove items that are in the given column range."""
        start = col
        stop = col + count
        for idx in list(self._dict.keys()):
            if start <= idx.column < stop:
                self.pop(idx)
            elif idx.column >= stop:
                new_idx = Index(idx.row, idx.column - count)
                child = self._dict.pop(idx)
                self._dict[new_idx] = child
                # if isinstance(child, TableAnchorBase):
                #     child.remove_columns(col, count)

        return None


class SlotRefMapping(MutableMapping[Index, InCellRangedSlot], TableAnchorBase):
    def __init__(self, table: TableBase) -> None:
        self._table_ref = weakref.ref(table)
        self._locked_pos = None

    def table(self) -> TableBase:
        if table := self._table_ref():
            return table
        raise RuntimeError("Table has been deleted")

    def __getitem__(self, source_key: Index) -> InCellRangedSlot:
        for slot in self.table().events.data.iter_slots():
            if not isinstance(slot, InCellRangedSlot):
                continue
            if slot.source_pos == source_key:
                return slot
        raise KeyError(source_key)

    def get_by_dest(self, source_key: Index, default=None) -> InCellRangedSlot:
        for slot in self.table().events.data.iter_slots():
            if not isinstance(slot, InCellRangedSlot):
                continue
            if slot.source_pos == source_key:
                return slot
            dest = slot.last_destination
            if dest is not None:
                rsl, csl = dest
                r, c = source_key
                if rsl.start <= r < rsl.stop and csl.start <= c < csl.stop:
                    return slot
        return default

    def __setitem__(self, key: Index, slot: InCellRangedSlot) -> None:
        if self._locked_pos == key:
            return
        if self.pop(key, None):
            logger.debug(f"Overwriting slot at {key}")
        self.table().events.data.connect_cell_slot(slot)
        logger.debug(f"Connecting slot at {key}")

    def __delitem__(self, source_key: Index) -> None:
        if self._locked_pos == source_key:
            return
        slot = self[source_key]
        self.table().events.data.disconnect(slot)
        logger.debug(f"Deleting slot at {source_key}")

    def _remove_multiple(self, slots: Iterable[InCellRangedSlot]):
        data = self.table().events.data
        for slot in slots:
            data.disconnect(slot)

    def __iter__(self) -> Iterator[Index]:
        for slot in self.table().events.data.iter_slots():
            if not isinstance(slot, InCellRangedSlot):
                continue
            yield Index(*slot.source_pos)

    def values(self):
        for slot in self.table().events.data.iter_slots():
            if not isinstance(slot, InCellRangedSlot):
                continue
            yield slot

    def items(self):
        for slot in self.table().events.data.iter_slots():
            if not isinstance(slot, InCellRangedSlot):
                continue
            yield Index(*slot.source_pos), slot

    def __len__(self) -> int:
        return len([i for i in self])

    @contextmanager
    def lock_pos(self, pos: Index):
        _old_pos = self._locked_pos
        self._locked_pos = pos
        try:
            yield
        finally:
            self._locked_pos = _old_pos

    def insert_rows(self, row: int, count: int):
        """Insert rows and update indices."""

    def insert_columns(self, col: int, count: int):
        """Insert columns and update indices."""

    def remove_rows(self, row: int, count: int):
        """Remove items that are in the given row range."""
        start = row
        stop = row + count
        rem = []
        for idx, slot in self.items():
            if start <= idx.column < stop:
                rem.append(slot)
        self._remove_multiple(rem)
        return None

    def remove_columns(self, col: int, count: int):
        """Remove items that are in the given column range."""
        start = col
        stop = col + count
        rem = []
        for idx, slot in self.items():
            if start <= idx.column < stop:
                rem.append(slot)
        self._remove_multiple(rem)
        return None


class DummySlotRefMapping(MutableMapping[Index, Any], TableAnchorBase):
    def table(self) -> TableBase:
        raise RuntimeError("This is dummy mapping")

    def __getitem__(self, key: Index) -> InCellRangedSlot:
        raise KeyError(key)

    def get_by_dest(self, key: Index, default=None) -> InCellRangedSlot:
        return default

    def __setitem__(self, key: Index, slot: InCellRangedSlot) -> None:
        raise KeyError(key)

    def __delitem__(self, key: Index) -> None:
        raise KeyError(key)

    def __iter__(self) -> Iterator[Index]:
        raise StopIteration

    def __len__(self) -> int:
        return 0

    @contextmanager
    def lock_pos(self, pos: Index):
        yield

    def insert_rows(self, row: int, count: int):
        """Insert rows and update indices."""

    def insert_columns(self, col: int, count: int):
        """Insert columns and update indices."""

    def remove_rows(self, row: int, count: int):
        """Remove items that are in the given row range."""

    def remove_columns(self, col: int, count: int):
        """Remove items that are in the given column range."""
