from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd

ORD_A = ord("A")


def str_to_num(s: str):
    out = 0
    for i, c in enumerate(reversed(s)):
        out += (ord(c) - ORD_A) ** (i + 1)
    return out


CHARS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + [""]
LONGEST = np.array(CHARS[:-1])


def iter_char(start: int, stop: int):
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


def char_arange(stop: int) -> np.ndarray:
    global LONGEST
    nmax = len(LONGEST)
    if stop <= nmax:
        return np.array(LONGEST[:stop])
    LONGEST = np.append(LONGEST, np.fromiter(iter_char(nmax, stop), dtype=object))
    return LONGEST.copy()


class UniqueName:
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return repr(self.name)

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other


CHAR_RANGE_INDEX = UniqueName("column_range")


def char_range_index(stop: int) -> pd.Index:
    return pd.Index(char_arange(stop), name=CHAR_RANGE_INDEX)


def is_ranged(index: pd.Index) -> bool:
    return isinstance(index, pd.RangeIndex) or index.name is CHAR_RANGE_INDEX


def as_not_ranged(index: pd.Index) -> None:
    if index.name is CHAR_RANGE_INDEX:
        index.name = None


def as_constructor(index: pd.Index) -> Callable[[int], pd.Index] | None:
    if isinstance(index, pd.RangeIndex):
        return pd.RangeIndex
    elif index.name is CHAR_RANGE_INDEX:
        return char_range_index
    else:
        return None
