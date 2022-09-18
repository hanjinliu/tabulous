from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

from ._dtype import DTypeMap

_N_CHUNK = 1000


class AbstractReader(ABC):
    @abstractmethod
    def __iter__(self):
        ...

    @abstractmethod
    def read(self, n: int = 0):
        ...

    @abstractmethod
    def read_range(self, start: int, stop: int) -> tuple[pd.DataFrame, bool]:
        ...


class ExpandingList(list):
    """This list can set values at the next index."""

    def __setitem__(self, key: int, value: Any) -> None:
        if key == len(self):
            self.append(value)
        else:
            super().__setitem__(key, value)


class TextFileReader(AbstractReader):
    def __init__(self, path: str | Path, chunksize: int = _N_CHUNK):
        self._path = path
        self._chunksize = chunksize
        self._memo = ExpandingList([0])
        self._start = 0
        self._stop = 0
        self._currow = 0
        self._max_row = -1
        self._reader = None
        self._to_memorize: set[int] = set()
        self._dtypes = DTypeMap()

    def set_range(self, start: int, stop: int):
        # NOTE: We must consider the header!
        self._start = start + 1
        self._stop = stop + 1

        self._reader = self.readlines()  # initialize generator
        self._to_memorize = set(
            np.arange(
                1,
                int(np.ceil(stop / self._chunksize)),
            )
            * self._chunksize
        )

    def readlines(self):
        chunk_idx_start = self._start // self._chunksize

        if chunk_idx_start < len(self._memo):
            # can seek to the last chunk
            pos = chunk_idx_start
        else:
            pos = len(self._memo) - 1

        with open(self._path) as f:
            readline = f.readline
            yield readline()  # return header

            f.seek(self._memo[pos])

            # read and skip lines until we reach the start
            for r in range(self._chunksize * pos, self._start):
                if r in self._to_memorize:
                    self._memo[r // self._chunksize] = f.tell()
                self._currow = r
                readline()

            for r in range(self._start, self._stop):
                if r in self._to_memorize:
                    self._memo[r // self._chunksize] = f.tell()
                self._currow = r
                yield readline()

    def __iter__(self):
        return self.readlines()

    def read(self, nrows: int = 0):
        self._max_row = -1  # file size may change
        try:
            return next(self._reader)
        except StopIteration:
            self._max_row = self._currow
            return ""

    def read_range(self, start: int, stop: int) -> tuple[pd.DataFrame, bool]:
        self.set_range(start, stop)
        df = pd.read_csv(self, **self._dtypes.as_pandas_kwargs())
        ended = self._currow == self._max_row
        return df, ended
