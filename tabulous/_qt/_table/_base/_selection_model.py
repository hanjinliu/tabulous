from __future__ import annotations
from typing import TYPE_CHECKING, Iterator
from contextlib import contextmanager

if TYPE_CHECKING:
    from ._enhanced_table import _QTableViewEnhanced
    from qtpy import QtCore

    Range = tuple[slice, slice]


class RangesModel:
    """Custom range model for efficient overlay handling on a large table."""

    def __init__(self):
        self._ranges: list[Range] = []
        self._blocked = False

    def __len__(self) -> int:
        return len(self._ranges)

    def add_dummy(self) -> None:
        """Add dummy ranges."""
        self._ranges.append((slice(0, 0), slice(0, 0)))
        return None

    def append(self, highlight: Range) -> None:
        self._ranges.append(highlight)
        return None

    def update_last(self, highlight: Range) -> None:
        self._ranges[-1] = highlight
        return None

    def set_highlights(self, highlights: list[Range]) -> None:
        if self._blocked:
            return None
        self._ranges.clear()
        return self._ranges.extend(highlights)

    def clear(self) -> None:
        """Clear all the selections"""
        return self._ranges.clear()

    @contextmanager
    def blocked(self) -> None:
        """Block selection updates in this context."""
        self._blocked = True
        try:
            yield
        finally:
            self._blocked = False

    def set_current(self, idx: int):
        rng = self._ranges.pop(idx)
        self._ranges.append(rng)
        return None

    def iter_ranges_under_index(
        self,
        row: int,
        col: int,
        *,
        reverse: bool = True,
    ) -> Iterator[tuple[int, Range]]:
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
        try:
            out = next(self.iter_ranges_under_index(row, col))
        except StopIteration:
            out = -1, None
        return out

    def rangeRects(self, qtable: _QTableViewEnhanced) -> list[QtCore.QRect]:
        model = qtable.model()
        _rects = []
        for rr, cc in self._ranges:
            top_left = model.index(rr.start, cc.start)
            bottom_right = model.index(rr.stop - 1, cc.stop - 1)
            rect = qtable.visualRect(top_left) | qtable.visualRect(bottom_right)
            _rects.append(rect)
        return _rects


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
        if self._selection_start is None and not self._blocked:
            self._selection_start = r, c
        self._shift_on = True

    def shift_end(self) -> None:
        self._selection_start = None
        self._shift_on = False

    def drag_start(self, r: int, c: int) -> None:
        """Start dragging selection at (r, c)."""
        if self._blocked:
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

    def set_highlights(self, selections: list[Range]) -> None:
        if self._blocked:
            return None
        self._ranges.clear()
        return self._ranges.extend(selections)

    def drag_to(self, r: int, c: int):
        """Drag to (r, c) to select cells."""
        if self._blocked:
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
