from __future__ import annotations
from typing import Iterator, MutableMapping, NamedTuple, TypeVar


class Index(NamedTuple):
    row: int
    column: int


_V = TypeVar("_V")


class TableMapping(MutableMapping[Index, _V]):
    def __init__(self) -> None:
        self._dict: dict[Index, _V] = {}

    def __getitem__(self, key: Index) -> _V:
        return self._dict[key]

    def __setitem__(self, key: tuple[int, int], value: _V) -> None:
        self._dict[Index(*key)] = value

    def __delitem__(self, key: Index) -> None:
        del self._dict[key]

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
