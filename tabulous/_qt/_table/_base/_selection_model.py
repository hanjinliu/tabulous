from __future__ import annotations
from typing import TYPE_CHECKING, Iterable, Iterator
from contextlib import contextmanager

if TYPE_CHECKING:

    Range = tuple[slice, slice]


class RangesModel:
    """Custom 2D range model for efficient overlay handling on a large table."""

    def __init__(self):
        self._ranges: list[Range] = []
        self._is_blocked = False
        self._selected_indices: set[int] = set()

    def __len__(self) -> int:
        return len(self._ranges)

    def add_dummy(self) -> None:
        """Add dummy ranges."""
        self._ranges.append((slice(0, 0), slice(0, 0)))
        return None

    def append(self, range: Range) -> None:
        self._ranges.append(range)
        return None

    def update_last(self, range: Range) -> None:
        if self._is_blocked:
            return None
        if self._ranges:
            self._ranges[-1] = range
        else:
            self._ranges.append(range)
        return None

    def set_ranges(self, ranges: list[Range]) -> None:
        if self._is_blocked:
            return None
        self._ranges.clear()
        return self._ranges.extend(ranges)

    def clear(self) -> None:
        """Clear all the selections"""
        return self._ranges.clear()

    @contextmanager
    def blocked(self) -> None:
        """Block selection updates in this context."""
        self._is_blocked = True
        try:
            yield
        finally:
            self._is_blocked = False

    def move_to_last(self, idx: int):
        rng = self._ranges.pop(idx)
        self._ranges.append(rng)
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

    def __init__(self):
        super().__init__()
        self._ctrl_on = False
        self._shift_on = False
        self._selection_start = None

    def set_ctrl(self, on: bool) -> None:
        """Equivalent to pressing Ctrl."""
        self._ctrl_on = bool(on)
        return None

    def set_shift(self, on: bool) -> None:
        """Equivalent to pressing Shift."""
        self._shift_on = bool(on)
        return None

    def shift_start(self, r: int, c: int) -> None:
        if self._selection_start is None and not self._is_blocked:
            self._selection_start = r, c
        self._shift_on = True

    def shift_end(self) -> None:
        self._selection_start = None
        self._shift_on = False

    def drag_start(self, r: int, c: int) -> None:
        """Start dragging selection at (r, c)."""
        if self._is_blocked:
            return None

        if not self._shift_on:
            self._selection_start = (r, c)

        if not self._ctrl_on:
            self.clear()
        else:
            self._ranges.append((slice(r, r + 1), slice(c, c + 1)))
        self.drag_to(r, c)
        return None

    def drag_end(self) -> None:
        """Finish dragging selection."""

    def set_ranges(self, selections: list[Range]) -> None:
        if self._is_blocked:
            return None
        self._ranges.clear()
        return self._ranges.extend(selections)

    def drag_to(self, r: int, c: int):
        """Drag to (r, c) to select cells."""
        if self._is_blocked:
            return None
        if self._selection_start is None:
            if not self._ctrl_on:
                self._ranges.clear()
            _r0 = _r1 = r
            _c0 = _c1 = c
        else:
            r0, c0 = self._selection_start
            _r0, _r1 = sorted([r0, r])
            _c0, _c1 = sorted([c0, c])

        if len(self._ranges) > 0:
            self._ranges[-1] = (slice(_r0, _r1 + 1), slice(_c0, _c1 + 1))
        else:
            self._ranges.append((slice(_r0, _r1 + 1), slice(_c0, _c1 + 1)))
        return None
