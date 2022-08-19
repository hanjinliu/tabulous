from __future__ import annotations
from contextlib import contextmanager


class SelectionModel:
    """Custom selection model for efficient selection handling on a large table."""

    def __init__(self):
        self._ctrl_on = False
        self._shift_on = False
        self._selection_start = None
        self._selections: list[tuple[slice, slice]] = []
        self._blocked = False

    def set_ctrl(self, on: bool) -> None:
        """Equivalent to pressing Ctrl."""
        self._ctrl_on = on
        return None

    def set_shift(self, on: bool) -> None:
        """Equivalent to pressing Shift."""
        self._shift_on = on
        return None

    def shift_start(self, r: int, c: int) -> None:
        if self._selection_start is None and not self._blocked:
            self._selection_start = r, c
        self._shift_on = True

    def shift_end(self) -> None:
        self._selection_start = None
        self._shift_on = False

    def add_dummy(self) -> None:
        self._selections.append((slice(0, 0), slice(0, 0)))
        return None

    def drag_start(self, r: int, c: int) -> None:
        """Start dragging selection at (r, c)."""
        if self._blocked:
            return None

        if not self._shift_on:
            self._selection_start = (r, c)

        if not self._ctrl_on:
            self.clear()
        else:
            self._selections.append((slice(r, r + 1), slice(c, c + 1)))
        self.drag_to(r, c)
        return None

    def drag_end(self) -> None:
        """Finish dragging selection."""

    def set_selections(self, selections: list[tuple[slice, slice]]) -> None:
        if self._blocked:
            return None
        self._selections.clear()
        return self._selections.extend(selections)

    def drag_to(self, r: int, c: int):
        """Drag to (r, c) to select cells."""
        if self._blocked:
            return None
        if self._selection_start is None:
            if not self._ctrl_on:
                self._selections.clear()
            _r0 = _r1 = r
            _c0 = _c1 = c
        else:
            r0, c0 = self._selection_start
            _r0, _r1 = sorted([r0, r])
            _c0, _c1 = sorted([c0, c])

        if len(self._selections) > 0:
            self._selections[-1] = (slice(_r0, _r1 + 1), slice(_c0, _c1 + 1))
        else:
            self._selections.append((slice(_r0, _r1 + 1), slice(_c0, _c1 + 1)))
        return None

    def clear(self) -> None:
        return self._selections.clear()

    @contextmanager
    def blocked(self) -> None:
        self._blocked = True
        try:
            yield
        finally:
            self._blocked = False
