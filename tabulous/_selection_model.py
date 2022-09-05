from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, NamedTuple
from contextlib import contextmanager
from psygnal import Signal

if TYPE_CHECKING:

    Range = tuple[slice, slice]


class Index(NamedTuple):
    """Index tuple,"""

    row: int
    column: int


class RangesModel:
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

    @property
    def ranges(self) -> list[Range]:
        return list(self._ranges)

    def iter_row_selections(self) -> Iterator[slice]:
        for i in self._row_selection_indices:
            yield self._ranges[i][0]

    def iter_col_selections(self) -> Iterator[slice]:
        for i in self._col_selection_indices:
            yield self._ranges[i][1]

    def add_dummy(self) -> None:
        """Add dummy ranges."""
        self._ranges.append((slice(0, 0), slice(0, 0)))
        return None

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
            self._row_selection_indices.pop(idx)
            self._row_selection_indices.add(len(self._ranges))
        elif idx in self._col_selection_indices:
            self._col_selection_indices.pop(idx)
            self._col_selection_indices.add(len(self._ranges))
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


class SelectionModel(RangesModel):
    """A specialized range model with item-selection-like behavior."""

    moved = Signal(Index)

    def __init__(self, row_count: Callable[[], int], col_count: Callable[[], int]):
        super().__init__()
        self._ctrl_on = False
        self._shift_on = False
        self._selection_start: Index | None = None
        self._index_current = Index(0, 0)
        self._row_count_getter = row_count
        self._col_count_getter = col_count

    @property
    def index_current(self) -> Index:
        return self._index_current

    @index_current.setter
    def index_current(self, index: tuple[int, int]):
        self._index_current = Index(*index)

    def set_ctrl(self, on: bool) -> None:
        """Equivalent to pressing Ctrl."""
        self._ctrl_on = bool(on)
        return None

    def set_shift(self, on: bool) -> None:
        """Equivalent to pressing Shift."""
        self._shift_on = bool(on)
        if self._selection_start is None:
            self._selection_start = self._index_current
        return None

    def reset(self) -> None:
        self._selection_start = None

    def set_ranges(self, selections: list[Range]) -> None:
        if self._is_blocked:
            return None
        self.clear()
        return self._ranges.extend(selections)

    def jump_to(self, r: int, c: int):
        """Emulate mouse click at cell (r, c)."""
        if self._ctrl_on and not self._shift_on:
            self.add_dummy()
        return self.move_to(r, c)

    def move_to(self, r: int, c: int):
        """Emulate dragging to cell (r, c)."""
        self._index_current = Index(r, c)
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
            row = True
        else:
            rsl = slice(_r0, _r1 + 1)
            row = False
        if _c0 < 0:
            csl = slice(0, self._col_count_getter())
            col = True
        else:
            csl = slice(_c0, _c1 + 1)
            col = False

        if not self._shift_on:
            if not self._ctrl_on:
                self.clear()
        elif self._selection_start is None:
            self._selection_start = self._index_current

        self.update_last((rsl, csl), row=row, col=col)
        self.moved.emit(self._index_current)
        return None

    def move(self, dr: int, dc: int, allow_header: bool = False):
        r, c = self._index_current
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
