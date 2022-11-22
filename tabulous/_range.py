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

        rlower = r0_s <= r0_o if r0_s is not None else True
        rupper = r1_o <= r1_s if r1_s is not None else True
        clower = c0_s <= c0_o if c0_s is not None else True
        cupper = c1_o <= c1_s if c1_s is not None else True

        return rlower and rupper and clower and cupper

    def overlaps_with(self, other: RectRange) -> bool:
        r0_s, r1_s = self._rsl.start, self._rsl.stop
        c0_s, c1_s = self._csl.start, self._csl.stop
        r0_o, r1_o = other._rsl.start, other._rsl.stop
        c0_o, c1_o = other._csl.start, other._csl.stop

        rlower = r0_s <= r0_o if r0_s is not None else True
        rupper = r1_o <= r1_s if r1_s is not None else True
        clower = c0_s <= c0_o if c0_s is not None else True
        cupper = c1_o <= c1_s if c1_s is not None else True

        return (rlower or rupper) and (clower or cupper)


class AnyRange(RectRange):
    """Contains any indices."""

    def __contains__(self, item) -> bool:
        return True

    def includes(self, other: RectRange) -> bool:
        return True

    def overlaps_with(self, other: RectRange) -> bool:
        return True


class NoRange:
    """Contains no index."""

    def __contains__(self, item) -> bool:
        return False

    def includes(self, other: RectRange) -> bool:
        return False

    def overlap_with(self, other: RectRange) -> bool:
        return False
