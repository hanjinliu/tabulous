from __future__ import annotations


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


class AnyRange(RectRange):
    """Contains any indices."""

    def __contains__(self, item) -> bool:
        return True


class NoRange:
    """Contains no index."""

    def __contains__(self, item) -> bool:
        return False
