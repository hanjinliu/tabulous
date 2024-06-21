from __future__ import annotations

import numpy as np

# utility functions for working with slices


def len_1(sl: slice) -> bool:
    """True if the slice is of length 1."""
    if sl.start is None:
        return sl.stop == 1
    elif sl.stop is None:
        return False
    return sl.stop - sl.start == 1


def in_range(i: int, sl: slice) -> bool:
    """True if i is in the range of the slice."""
    if sl.start is None:
        if sl.stop is None:
            return True
        else:
            return i < sl.stop
    else:
        if sl.stop is None:
            return sl.start <= i
        else:
            return sl.start <= i < sl.stop


def len_of(sl: slice, size: int | None = None, allow_negative: bool = False) -> int:
    """Length of the slice, given the size of the sequence."""
    if size is not None:
        start, stop, _ = sl.indices(size)
    else:
        start, stop = sl.start, sl.stop
        if start is None or stop is None:
            raise ValueError(f"size must be given if slice has None: {fmt(sl)}")
    if not allow_negative:
        if start < 0 or stop < 0:
            raise ValueError(f"negative indices not allowed: {fmt(sl)}")
    return stop - start


def as_sized(sl: slice, size: int, allow_negative: bool = False):
    start, stop, _ = sl.indices(size)
    if not allow_negative:
        if start < 0 or stop < 0:
            raise ValueError(f"negative indices not allowed: {fmt(sl)}")
    return slice(start, stop)


def fmt(sl: slice) -> str:
    """Format a slice as a string."""
    if isinstance(sl, slice):
        s0 = _repr(sl.start) if sl.start is not None else ""
        s1 = _repr(sl.stop) if sl.stop is not None else ""
        return f"{s0}:{s1}"
    return _repr(sl)


def has_none(sl: slice):
    return sl.start is None or sl.stop is None


def _repr(x) -> str:
    if isinstance(x, np.number):
        return str(x)
    return repr(x)
