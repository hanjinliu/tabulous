from __future__ import annotations


class RectRange:
    def __init__(
        self,
        rsl: slice = slice(0, 0),
        csl: slice = slice(0, 0),
    ):
        self._rsl = rsl
        self._csl = csl

    def __repr__(self):
        return f"RectRange[{_fmt_slice(self._rsl)}, {_fmt_slice(self._csl)}]"

    def __contains__(self, other: tuple[int, int]):
        r, c = other
        rsl = self._rsl
        csl = self._csl
        rlower = rsl.start <= r if rsl.start is not None else True
        rupper = r < rsl.stop if rsl.stop is not None else True
        clower = csl.start <= c if csl.start is not None else True
        cupper = c < csl.stop if csl.stop is not None else True
        return rlower and rupper and clower and cupper

    def includes(self, other: RectRange) -> bool:
        r0_s, r1_s = self._rsl.start, self._rsl.stop
        c0_s, c1_s = self._csl.start, self._csl.stop
        r0_o, r1_o = other._rsl.start, other._rsl.stop
        c0_o, c1_o = other._csl.start, other._csl.stop

        return (
            _le(r0_s, r0_o) and _ge(r1_s, r1_o) and _le(c0_s, c0_o) and _ge(c1_s, c1_o)
        )

    def overlaps_with(self, other: RectRange) -> bool:
        r0_s, r1_s = self._rsl.start, self._rsl.stop
        c0_s, c1_s = self._csl.start, self._csl.stop
        r0_o, r1_o = other._rsl.start, other._rsl.stop
        c0_o, c1_o = other._csl.start, other._csl.stop

        return _overlap_1d(r0_s, r1_s, r0_o, r1_o) and _overlap_1d(
            c0_s, c1_s, c0_o, c1_o
        )

    def insert_rows(self, row: int, count: int) -> None:
        """Insert rows and update slices in-place."""
        self._rsl = _translate_slice(self._rsl, row, count)
        return None

    def insert_columns(self, col: int, count: int) -> None:
        """Insert columns and update slices in-place."""
        self._csl = _translate_slice(self._csl, col, count)
        return None

    def remove_rows(self, row: int, count: int):
        """Remove rows and update slices in-place."""
        self._rsl = _translate_slice(self._rsl, row, -count)
        return None

    def remove_columns(self, col: int, count: int):
        """Remove columns and update slices in-place."""
        self._csl = _translate_slice(self._csl, col, -count)
        return None

    def is_empty(self) -> bool:
        """True if the range is empty."""
        r0_s, r1_s = self._rsl.start, self._rsl.stop
        c0_s, c1_s = self._csl.start, self._csl.stop
        if r0_s is None or r1_s is None or c0_s is None or c1_s is None:
            return False
        return self._rsl.start >= self._rsl.stop and self._csl.start >= self._csl.stop


_DO_NOTHING = lambda *args, **kwargs: None


class AnyRange(RectRange):
    """Contains any indices."""

    def __init__(self):
        super().__init__(slice(None), slice(None))

    def __contains__(self, item) -> bool:
        return True

    def __repr__(self):
        return f"AnyRange[...]"

    def includes(self, other: RectRange) -> bool:
        return True

    def overlaps_with(self, other: RectRange) -> bool:
        return True

    insert_rows = _DO_NOTHING
    insert_columns = _DO_NOTHING
    remove_rows = _DO_NOTHING
    remove_columns = _DO_NOTHING

    def is_empty(self) -> bool:
        return False


class NoRange(RectRange):
    """Contains no index."""

    def __init__(self):
        super().__init__(slice(0, -1), slice(0, -1))

    def __contains__(self, item) -> bool:
        return False

    def __repr__(self):
        return f"NoRange[...]"

    def includes(self, other: RectRange) -> bool:
        return False

    def overlap_with(self, other: RectRange) -> bool:
        return False

    insert_rows = _DO_NOTHING
    insert_columns = _DO_NOTHING
    remove_rows = _DO_NOTHING
    remove_columns = _DO_NOTHING

    def is_empty(self) -> bool:
        return True


def _fmt_slice(sl: slice) -> str:
    s0 = sl.start if sl.start is not None else ""
    s1 = sl.stop if sl.stop is not None else ""
    return f"{s0}:{s1}"


def _le(r0_s, r0_o):
    if r0_s is not None:
        if r0_o is None:
            return False
        else:
            return r0_s <= r0_o
    else:
        return True


def _ge(r1_s, r1_o):
    if r1_s is not None:
        if r1_o is None:
            return False
        else:
            return r1_o <= r1_s
    else:
        return True


INF = float("inf")


def _overlap_1d(
    r0_s: int | None, r1_s: int | None, r0_o: int | None, r1_o: int | None
) -> bool:
    if r0_s is None:
        r0_s = 0
    if r1_s is None:
        r1_s = INF
    if r0_o is None:
        r0_o = 0
    if r1_o is None:
        r1_o = INF

    return r0_o < r1_s and r0_s < r1_o


def _translate_slice(sl: slice, index: int, count: int) -> slice:
    start, stop = sl.start, sl.stop

    if start is not None and start >= index:
        start = start + count
    if stop is not None and stop >= index:
        stop = stop + count

    return slice(start, stop)
