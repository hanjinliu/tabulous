from __future__ import annotations

# TODO: consider slice(None)
class RectRange:
    def __init__(
        self,
        rsl: slice = slice(0, 0),
        csl: slice = slice(0, 0),
    ):
        self._rsl = rsl
        self._csl = csl

    def __contains__(self, other: tuple[int, int]):
        r, c = other
        rsl = self._rsl
        csl = self._csl
        return rsl.start <= r < rsl.stop and csl.start <= c < csl.stop

    def includes(self, other: RectRange) -> bool:
        r0_s, r1_s = self._rsl.start, self._rsl.stop
        c0_s, c1_s = self._csl.start, self._csl.stop
        r0_o, r1_o = other._rsl.start, other._rsl.stop
        c0_o, c1_o = other._csl.start, other._csl.stop

        return r0_s <= r0_o and r1_o <= r1_s and c0_s <= c0_o and c1_o <= c1_s

    def overlap_with(self, other: RectRange) -> bool:
        r0_s, r1_s = self._rsl.start, self._rsl.stop
        c0_s, c1_s = self._csl.start, self._csl.stop
        r0_o, r1_o = other._rsl.start, other._rsl.stop
        c0_o, c1_o = other._csl.start, other._csl.stop

        return (r0_s < r1_o or r0_o < r1_s) and (c0_s < c1_o or c0_o < c1_s)


class AnyRange(RectRange):
    """Contains any indices."""

    def __contains__(self, item) -> bool:
        return True


class NoRange:
    """Contains no index."""

    def __contains__(self, item) -> bool:
        return False
