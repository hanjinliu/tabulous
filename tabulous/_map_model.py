from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator, MutableMapping, NamedTuple, TypeVar, TYPE_CHECKING
from psygnal import Signal
import logging

if TYPE_CHECKING:
    from tabulous._range import RectRange


class Index(NamedTuple):
    row: int
    column: int


_V = TypeVar("_V")

logger = logging.getLogger(__name__)


class TableMapping(MutableMapping[Index, _V]):
    set = Signal(Index, object)
    deleted = Signal(object)

    def __init__(self) -> None:
        self._dict: dict[Index, _V] = {}
        from tabulous._range import NoRange

        self._marked_range = NoRange()

    def __getitem__(self, key: Index) -> _V:
        return self._dict[key]

    def __setitem__(self, key: tuple[int, int], value: _V) -> None:
        logger.debug(f"Setting TableMapping item at {key}")
        self._dict[Index(*key)] = value
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
                graph = self._dict.pop(idx)
                new_dict[new_idx] = graph

        self._dict.update(new_dict)
        return None

    def insert_columns(self, col: int, count: int):
        """Insert columns and update indices."""
        new_dict = {}
        for idx in list(self._dict.keys()):
            if idx.column >= col:
                new_idx = Index(idx.row, idx.column + count)
                graph = self._dict.pop(idx)
                new_dict[new_idx] = graph

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
                graph = self._dict.pop(idx)
                self._dict[new_idx] = graph

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
                graph = self._dict.pop(idx)
                self._dict[new_idx] = graph

        return None

    @contextmanager
    def mark_range(self, rng: RectRange):
        _old_range = self._marked_range
        self._marked_range = rng
        try:
            yield
        finally:
            self._marked_range = _old_range

    def is_marking(self, rng: RectRange) -> bool:
        return self._marked_range.includes(rng)
