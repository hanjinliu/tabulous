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


def _overlap_1d(r0_s, r1_s, r0_o, r1_o):
    if r0_s is None:
        r0_s = 0
    if r1_s is None:
        r1_s = INF
    if r0_o is None:
        r0_o = 0
    if r1_o is None:
        r1_o = INF

    return r0_o < r1_s and r0_s < r1_o
