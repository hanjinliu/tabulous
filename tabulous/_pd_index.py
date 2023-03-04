from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd

ORD_A = ord("A")
CHARS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + [""]
CHARS_SET = set(CHARS)
LONGEST = np.array(CHARS[:-1], dtype=object)


def str_to_num(s: str):
    """Converts an Excel-like column label to an integer."""
    result = -1
    for i, char in enumerate(reversed(s)):
        result += (ord(char) - 64) * (26**i)
    return result


def num_to_str(n: int) -> str:
    """Converts an integer to an Excel-like column label."""
    n += 1
    results: list[str] = []
    while n > 0:
        n -= 1
        remainder = n % 26
        results.append(CHARS[remainder])
        n //= 26
    return "".join(reversed(results))


def increment(s: str, d: int) -> str:
    """Increment an Excel-like column label."""
    return num_to_str(str_to_num(s) + d)


def decrement(s: str, d: int) -> str:
    """Decrement an Excel-like column label."""
    return num_to_str(str_to_num(s) - d)


def is_between(s: str, start: int, stop: int) -> bool:
    """Check if a string is between two integers."""
    return start <= num_to_str(s) <= stop


def _iter_char(start: int, stop: int):
    if stop >= 26**4:
        raise ValueError("Stop must be less than 26**4 - 1")
    base_repr = np.base_repr(start, 26)
    current = np.zeros(4, dtype=np.int8)
    offset = 4 - len(base_repr)
    for i, d in enumerate(base_repr):
        current[i + offset] = int(d, 26)

    current[:3] -= 1
    for _ in range(start, stop):
        yield "".join(CHARS[s] for s in current)
        current[3] += 1
        for i in [3, 2, 1]:
            if current[i] >= 26:
                over = current[i] - 25
                current[i] = 0
                current[i - 1] += over


def char_arange(start: int, stop: int = None) -> np.ndarray:
    """
    A char version of np.arange.

    Examples
    --------
    >>> char_arange(3)  # array(["A", "B", "C"])
    >>> char_arange(25, 28)  # array(["Z", "AA", "AB"])
    """
    global LONGEST
    if stop is None:
        start, stop = 0, start
    nmax = len(LONGEST)
    if stop <= nmax:
        return np.array(LONGEST[start:stop], dtype=object)
    LONGEST = np.append(LONGEST, np.fromiter(_iter_char(nmax, stop), dtype=object))
    return LONGEST[start:].copy()


class UniqueName:
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"UniqueName({self.name!r})"

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other


HEADER = UniqueName("header")


def char_range_index(stop: int) -> pd.Index:
    """Make an index with values A, B, C, ..."""
    return pd.Index(char_arange(stop), name=HEADER)


def is_ranged(index: pd.Index) -> bool:
    """Check if given index is range-like."""
    return isinstance(index, pd.RangeIndex) or index.name is HEADER


def as_not_ranged(index: pd.Index) -> None:
    if index.name is HEADER:
        index.name = None


def as_constructor(index: pd.Index) -> Callable[[int], pd.Index] | None:
    if isinstance(index, pd.RangeIndex):
        return pd.RangeIndex
    elif index.name is HEADER:
        return char_range_index
    else:
        return None
