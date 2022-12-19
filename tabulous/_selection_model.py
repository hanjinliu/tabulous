from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, NamedTuple
from contextlib import contextmanager
from psygnal import Signal

from tabulous._range import TableAnchorBase, translate_slice

if TYPE_CHECKING:
    Range = tuple[slice, slice]


class Index(NamedTuple):
    """Index tuple,"""

    row: int
    column: int

    def as_uint(self) -> Index:
        """Return unsigned Index"""
        return Index(max(self.row, 0), max(self.column, 0))


class DummyRange(NamedTuple):
    row: slice
    column: slice


_DUMMY_RANGE = DummyRange(slice(0, 0), slice(0, 0))


class RangesModel(TableAnchorBase):
    """Custom 2D range model for efficient overlay handling on a large table."""

    def __init__(self):
        self._ranges: list[Range] = []
        self._is_blocked = False
        self._selected_indices: set[int] = set()
        self._row_selection_indices: set[int] = set()
        self._col_selection_indices: set[int] = set()

    def __len__(self) -> int:
        """Number of ranges"""
        return len(self._ranges)

    def __iter__(self) -> Iterator[Range]:
        """Iterate over all the ranges."""
        return iter(self._ranges)

    def __getitem__(self, index: int) -> Range:
        """Get the range at the specified index."""
        return self._ranges[index]

    @property
    def ranges(self) -> list[Range]:
        return list(self._ranges)

    def iter_row_selections(self) -> Iterator[slice]:
        for i in self._row_selection_indices:
            yield self._ranges[i][0]

    def iter_col_selections(self) -> Iterator[slice]:
        for i in self._col_selection_indices:
            yield self._ranges[i][1]

    def as_ranges(self) -> list[Range]:
        """Return a list of ranges considering row/column selections."""
        out: list[Range] = []
        for i, rng in enumerate(self._ranges):
            if i in self._row_selection_indices:
                if i in self._col_selection_indices:
                    out.append((slice(None), slice(None)))
                else:
                    out.append((rng[0], slice(None)))
            elif i in self._col_selection_indices:
                out.append((slice(None), rng[1]))
            else:
                out.append(rng)
        return out

    def append(self, range: Range, row: bool = False, column: bool = False) -> None:
        """Append a new range."""
        if self._is_blocked:
            return None
        self._ranges.append(range)
        if row:
            self._row_selection_indices.add(len(self._ranges) - 1)
        elif column:
            self._col_selection_indices.add(len(self._ranges) - 1)
        return None

    def update_last(self, range: Range, row: bool = False, col: bool = False) -> None:
        """Update the last range with new one."""
        if self._is_blocked:
            return None
        if self._ranges:
            self._ranges[-1] = range
        else:
            self._ranges.append(range)
        if row:
            self._row_selection_indices.add(len(self._ranges) - 1)
        elif col:
            self._col_selection_indices.add(len(self._ranges) - 1)
        return None

    def set_ranges(self, ranges: list[Range]) -> None:
        if self._is_blocked:
            return None
        self.clear()
        return self._ranges.extend(ranges)

    def clear(self) -> None:
        """Clear all the selections"""
        if self._is_blocked:
            return None
        self._ranges.clear()
        self._row_selection_indices.clear()
        self._col_selection_indices.clear()
        return None

    @contextmanager
    def blocked(self) -> None:
        """Block selection updates in this context."""
        self._is_blocked = True
        try:
            yield
        finally:
            self._is_blocked = False

    def reorder_to_last(self, idx: int):
        rng = self._ranges.pop(idx)
        self._ranges.append(rng)
        if idx in self._row_selection_indices:
            self._row_selection_indices.discard(idx)
            self._row_selection_indices.add(len(self._ranges) - 1)
        elif idx in self._col_selection_indices:
            self._col_selection_indices.discard(idx)
            self._col_selection_indices.add(len(self._ranges) - 1)
        return None

    def select(self, indices: Iterable[int]) -> None:
        self._selected_indices = set(indices)
        return None

    def add_selection(self, index: int) -> None:
        nranges = len(self._ranges)
        if index < 0:
            index += nranges
        if 0 <= index < nranges:
            self._selected_indices.add(index)
        else:
            raise ValueError(f"Index {index} out of range")
        return None

    def delete_selected(self):
        remain = [
            self._ranges[i]
            for i in range(len(self._ranges))
            if i not in self._selected_indices
        ]
        self._ranges = remain
        self._row_selection_indices -= self._selected_indices
        self._col_selection_indices -= self._selected_indices
        self._selected_indices = set()
        return None

    def iter_ranges_under_index(
        self,
        row: int,
        col: int,
        *,
        reverse: bool = True,
    ) -> Iterator[tuple[int, Range]]:
        """Iterate over all the ranges that are under the specified position."""
        if reverse:
            rmax = len(self._ranges) - 1
            for i, (rr, cc) in enumerate(reversed(self._ranges)):
                if rr.start <= row < rr.stop and cc.start <= col < cc.stop:
                    yield rmax - i, (rr, cc)
        else:
            for i, (rr, cc) in enumerate(self._ranges):
                if rr.start <= row < rr.stop and cc.start <= col < cc.stop:
                    yield i, (rr, cc)

    def range_under_index(self, row: int, col: int) -> tuple[int, Range | None]:
        """Get the last range that is under the specified position."""
        try:
            out = next(self.iter_ranges_under_index(row, col))
        except StopIteration:
            out = -1, None
        return out

    def insert_rows(self, row: int, count: int) -> None:
        for i, (r, c) in enumerate(self._ranges):
            r = translate_slice(r, row, count)
            self._ranges[i] = (r, c)

    def insert_columns(self, col: int, count: int) -> None:
        for i, (r, c) in enumerate(self._ranges):
            c = translate_slice(c, col, count)
            self._ranges[i] = (r, c)

    def remove_rows(self, row: int, count: int) -> None:
        to_be_removed = []
        for i, (r, c) in enumerate(self._ranges):
            r = translate_slice(r, row, -count)
            if r.start >= r.stop:
                to_be_removed.append(i)
            self._ranges[i] = (r, c)
        for i in reversed(to_be_removed):
            self._ranges.pop(i)

    def remove_columns(self, col: int, count: int) -> None:
        to_be_removed = []
        for i, (r, c) in enumerate(self._ranges):
            c = translate_slice(c, col, -count)
            if c.start >= c.stop:
                to_be_removed.append(i)
            self._ranges[i] = (r, c)
        for i in reversed(to_be_removed):
            self._ranges.pop(i)


class SelectionModel(RangesModel):
    """A specialized range model with item-selection-like behavior."""

    moving = Signal(Index, Index)
    moved = Signal(Index, Index)

    def __init__(self, row_count: Callable[[], int], col_count: Callable[[], int]):
        super().__init__()
        self._ctrl_on = False
        self._shift_on = False
        self._selection_start: Index | None = None
        self._current_index = Index(0, 0)
        self._row_count_getter = row_count
        self._col_count_getter = col_count

    @property
    def current_index(self) -> Index:
        """Current position of the selection cursor."""
        return self._current_index

    @current_index.setter
    def current_index(self, index: tuple[int, int]):
        self._current_index = Index(*index)

    @property
    def current_range(self) -> tuple[slice, slice] | None:
        if len(self._ranges) > 0:
            return self._ranges[-1]
        return None

    def iter_all_indices(self) -> Iterator[tuple[int, int]]:
        """Iterate all the indices (int, int) in all the selection ranges."""
        nr = self._row_count_getter()
        nc = self._col_count_getter()
        for rng in self.ranges:
            for r in range(*rng[0].indices(nr)):
                for c in range(*rng[1].indices(nc)):
                    yield r, c

    @property
    def start(self) -> Index | None:
        """The selection starting index."""
        return self._selection_start

    def is_jumping(self) -> bool:
        """Whether the selection is jumping or not."""
        return len(self._ranges) > 0 and self._ranges[-1] is _DUMMY_RANGE

    def is_moving_to_edge(self) -> bool:
        """Whether the selection is moving to the edge by Ctrl+arrow key."""
        return not self.is_jumping() and self._ctrl_on

    def set_ctrl(self, on: bool) -> None:
        """Equivalent to pressing Ctrl."""
        self._ctrl_on = bool(on)
        return None

    def set_shift(self, on: bool) -> None:
        """Equivalent to pressing Shift."""
        self._shift_on = bool(on)
        if on and self._selection_start is None:
            self._selection_start = self._current_index
        return None

    def reset(self) -> None:
        self._selection_start = None

    def jump_to(self, r: int, c: int):
        """Emulate mouse click at cell (r, c)."""
        if self._ctrl_on and not self._shift_on:
            self._ranges.append(_DUMMY_RANGE)
        return self.move_to(r, c)

    def move_to(self, r: int, c: int):
        """Emulate dragging to cell (r, c)."""
        src = self._current_index
        dst = Index(r, c)
        self.moving.emit(src, dst)
        self._current_index = dst
        if self._is_blocked:
            return None

        if not self._shift_on:
            self._selection_start = None

        if self._selection_start is None:
            _r0 = _r1 = r
            _c0 = _c1 = c
        else:
            r0, c0 = self._selection_start
            _r0, _r1 = sorted([r0, r])
            _c0, _c1 = sorted([c0, c])

        if _r0 < 0:
            rsl = slice(0, self._row_count_getter())
            col = True
        else:
            rsl = slice(_r0, _r1 + 1)
            col = False
        if _c0 < 0:
            csl = slice(0, self._col_count_getter())
            row = True
        else:
            csl = slice(_c0, _c1 + 1)
            row = False

        if not self._shift_on:
            if not self.is_jumping():
                self.clear()
        elif self._selection_start is None:
            self._selection_start = self._current_index

        self.update_last((rsl, csl), row=row, col=col)
        self.moved.emit(src, dst)
        return None

    def move(self, dr: int, dc: int, allow_header: bool = False):
        """Move by (dr, dc) cells."""
        r, c = self._current_index
        idx_min = -int(allow_header)

        if dr != 0:
            nr = self._row_count_getter()
            r = min(r + dr, nr - 1)
            r = max(idx_min, r)

        if dc != 0:
            nc = self._col_count_getter()
            c = min(c + dc, nc - 1)
            c = max(idx_min, c)

        return self.move_to(r, c)
