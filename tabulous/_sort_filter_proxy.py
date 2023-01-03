from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Callable, NamedTuple, overload
import numpy as np
from enum import Enum
from tabulous.types import ProxyType, _IntArray, _IntOrBoolArray
from functools import reduce

if TYPE_CHECKING:
    import pandas as pd
    from typing_extensions import Self


class ProxyTypes(Enum):
    none = "none"
    unknown = "unknown"
    filter = "filter"
    sort = "sort"

    def __eq__(self, other: ProxyTypes | str) -> bool:
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)


class SortFilterProxy:
    """A custom sort/filter proxy for pandas dataframes."""

    def __init__(self, obj: ProxyType | None = None):
        if isinstance(obj, SortFilterProxy):
            obj = obj._obj
        if isinstance(obj, Composable) and obj.is_identity():
            obj = None
        self._obj: ProxyType | None = obj
        if self._obj is None:
            self._proxy_type = ProxyTypes.none
            self._is_ordered = True
        else:
            self._proxy_type = ProxyTypes.unknown
            self._is_ordered = False
        self._last_indexer = None

    def __repr__(self) -> str:
        cname = type(self).__name__
        return f"{cname}<proxy_type={self.proxy_type}, obj={self._obj!r}>"

    @property
    def proxy_type(self) -> ProxyTypes:
        """The proxy type."""
        return self._proxy_type

    @property
    def is_ordered(self) -> bool:
        return self._is_ordered

    @property
    def last_indexer(self) -> _IntOrBoolArray | None:
        return self._last_indexer

    def apply(
        self,
        df: pd.DataFrame,
        ref: pd.DataFrame | Callable[[], pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        """
        Apply the proxy rule to the dataframe.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe to be sliced.
        ref : pd.DataFrame, optional
            The reference dataframe to be used to determine the slice, if proxy is
            callable. If not given, ``df`` will be used. If a callable is given,
            it will be called to supply the reference dataframe.
        """
        sl = self._obj
        if sl is None:
            return df
        # get indexer
        if callable(sl):
            if ref is None:
                ref_input = df
            elif callable(ref):
                ref_input = ref()
            sl_filt = sl(ref_input)
        else:
            sl_filt = sl

        self._last_indexer = sl_filt

        if self._array_is_bool(sl_filt):
            df_filt = df[sl_filt]
        else:
            df_filt = df.iloc[sl_filt]
        return df_filt

    # fmt: off
    @overload
    def get_source_index(self, r: int) -> int: ...
    @overload
    def get_source_index(self, r: slice) -> slice | _IntArray: ...
    @overload
    def get_source_index(self, r: list[int]) -> _IntArray: ...
    # fmt: on

    def get_source_index(self, r):
        """Get the source index of the row in the dataframe."""
        sl = self._obj
        if sl is None:
            if isinstance(r, list):
                r = np.array(r)
            r0 = r
        else:
            if callable(sl):
                if self._last_indexer is not None:
                    sl = self._last_indexer
                else:
                    raise RuntimeError("Call apply first!")

            if self._array_is_bool(sl):
                sl = np.where(sl)[0]
            r0 = sl[r]
        return r0

    def get_source_slice(self, r: slice) -> slice:
        """Get the source row slice in the dataframe."""
        if self.proxy_type is ProxyTypes.none:
            return r
        start, stop = r.start, r.stop
        if start is None:
            start = 0
        if stop is None:
            if self._last_indexer is None:
                raise ValueError("Cannot determine stop index")
            stop = self._last_indexer.size
        start, stop = self.get_source_index([start, stop - 1])
        return slice(start, stop + 1)

    def map_slice(self, r: slice) -> slice:
        if self.proxy_type is ProxyTypes.none:
            return r
        start, stop = r.start, r.stop
        if start is None:
            start = 0
        if stop is None:
            if self._last_indexer is None:
                raise ValueError("Cannot determine stop index")
            stop = self._last_indexer.size
        # NOTE: mapping is not defined for all sources. For example, filter slice
        # [True, False, True] cannot map 1 because it does not exist in the
        # filtered data.
        if self._array_is_bool(self._last_indexer):
            _cumsum = np.cumsum(self._last_indexer)
            return slice(max(_cumsum[start] - 1, 0), max(_cumsum[stop - 1], 0))
        elif start == stop - 1:
            indices = np.where(self._last_indexer == start)[0]
            if len(indices) > 0:
                idx = indices[0]
                return slice(idx, idx + 1)
            raise ValueError(f"Cannot map slice {r} to source")
        else:
            raise ValueError("Cannot map slice if proxy is not ordered.")

    def as_indexer(self, df: pd.DataFrame | None) -> _IntOrBoolArray | slice:
        sl = self._obj
        if sl is None:
            return slice(None)
        if callable(sl):
            if self._last_indexer is not None:
                sl_filt = self._last_indexer
            else:
                if df is None:
                    raise ValueError("Cannot determine indexer")
                sl_filt = sl(df)
        else:
            sl_filt = sl
        return sl_filt

    def _array_is_bool(self, sl: _IntOrBoolArray) -> bool:
        if sl.dtype.kind == "b":
            self._proxy_type = ProxyTypes.filter
            self._is_ordered = True
        elif sl.dtype.kind in "ui":
            self._proxy_type = ProxyTypes.sort
            self._is_ordered = False
        else:
            raise TypeError(f"Invalid filter type: {sl.dtype}")
        return self._is_ordered


class FilterType(Enum):
    """Filter type enumeration."""

    none = "none"
    eq = "eq"
    ne = "ne"
    gt = "gt"
    ge = "ge"
    lt = "lt"
    le = "le"
    between = "between"
    isin = "isin"
    startswith = "startswith"
    endswith = "endswith"
    contains = "contains"
    matches = "matches"

    @property
    def repr(self) -> str:
        return _REPR_MAP[self]

    @property
    def requires_number(self) -> bool:
        cls = type(self)
        return self in {cls.eq, cls.ne, cls.gt, cls.ge, cls.lt, cls.le}

    @property
    def requires_text(self) -> bool:
        cls = type(self)
        return self in {
            cls.between,
            cls.startswith,
            cls.endswith,
            cls.contains,
            cls.matches,
        }

    @property
    def requires_list(self) -> bool:
        return self is FilterType.isin

    def __str__(self) -> str:
        return self.repr


def _is_between(x: pd.Series, a: str) -> pd.Series:
    a = a.strip()
    left = a[0]
    right = a[-1]
    values = [float(s.strip()) for s in a[1:-1].split(",")]
    if left == "[" and right == "]":
        inclusive = "both"
    elif left == "[" and right == ")":
        inclusive = "left"
    elif left == "(" and right == "]":
        inclusive = "right"
    elif left == "(" and right == ")":
        inclusive = "neither"
    else:
        raise ValueError(f"Invalid range: {a}")
    if len(values) != 2:
        raise ValueError(f"Invalid range: {a}")
    return x.between(*values, inclusive=inclusive)


_FUNCTION_MAP: dict[FilterType, Callable[[pd.Series, Any], pd.Series]] = {
    FilterType.none: lambda x, a: np.ones(len(x), dtype=bool),
    FilterType.eq: lambda x, a: x == a,
    FilterType.ne: lambda x, a: x != a,
    FilterType.gt: lambda x, a: x > a,
    FilterType.ge: lambda x, a: x >= a,
    FilterType.lt: lambda x, a: x < a,
    FilterType.le: lambda x, a: x <= a,
    FilterType.between: _is_between,
    FilterType.isin: lambda x, a: x.isin(a),
    FilterType.startswith: lambda x, a: x.str.startswith(a),
    FilterType.endswith: lambda x, a: x.str.endswith(a),
    FilterType.contains: lambda x, a: x.str.contains(a),
    FilterType.matches: lambda x, a: x.str.contains(a, regex=True),
}

_REPR_MAP: dict[FilterType, str] = {
    FilterType.none: "Select ...",
    FilterType.eq: "=",
    FilterType.ne: "≠",
    FilterType.gt: ">",
    FilterType.ge: "≥",
    FilterType.lt: "<",
    FilterType.le: "≤",
    FilterType.isin: "is in",
    FilterType.startswith: "starts with",
    FilterType.between: "between",
    FilterType.endswith: "ends with",
    FilterType.contains: "contains",
    FilterType.matches: ".*",
}


class FilterInfo(NamedTuple):
    type: FilterType
    arg: Any


class Composable:
    @abstractmethod
    def __call__(self, df: pd.DataFrame) -> np.ndarray:
        """Apply the mapping to the dataframe."""

    @abstractmethod
    def copy(self) -> Self:
        """Copy the instance."""

    @abstractmethod
    def compose(self, column: int) -> Self:
        """Compose with an additional mapping at the column."""

    @abstractmethod
    def decompose(self, column: int) -> Self:
        """Decompose the mapping at column."""

    @abstractmethod
    def is_identity(self) -> bool:
        """True if this instance is the identity mapping."""


class ComposableFilter(Composable):
    def __init__(self, d: dict[int, FilterInfo] | None = None):
        if d is not None:
            assert isinstance(d, dict)
            self._dict: dict[int, FilterInfo] = d
        else:
            self._dict = {}
        self.__name__ = "filter"
        self.__annotations__ = {"df": "pd.DataFrame", "return": np.ndarray}

    def __call__(self, df: pd.DataFrame) -> np.ndarray:
        series: list[pd.Series] = []
        if len(self._dict) == 0:
            return np.ones(len(df), dtype=bool)
        for index, (type, arg) in self._dict.items():
            fn = _FUNCTION_MAP[type]
            series.append(np.asarray(fn(df.iloc[:, index], arg)))
        return reduce(lambda x, y: x & y, series)

    def copy(self) -> ComposableFilter:
        """Copy the filter object."""
        return self.__class__(self._dict.copy())

    def compose(self, column: int, info: FilterInfo) -> ComposableFilter:
        """Compose with an additional column filter."""
        if info.type is FilterType.none:
            return self
        new = self.copy()
        new._dict[column] = info
        return new

    def decompose(self, column: int) -> ComposableFilter:
        """Decompose the filter at column."""
        new = self.copy()
        new._dict.pop(column, None)
        return new

    def is_identity(self) -> bool:
        """True if the filter is the identity filter."""
        return len(self._dict) == 0


class ComposableSorter(Composable):
    def __init__(self, columns: set[int] | None = None, ascending: bool = True):
        if columns is None:
            self._columns: set[int] = set()
        else:
            assert isinstance(columns, set)
            self._columns = columns
        self._ascending = ascending

    def __call__(self, df: pd.DataFrame) -> pd.Series:
        by: list[str] = [df.columns[i] for i in self._columns]
        if len(by) == 1:
            out = np.asarray(df[by[0]].argsort())
            if not self._ascending:
                out = out[::-1]
        else:
            df_sub = df[by]
            nr = len(df_sub)
            df_sub.index = range(nr)
            df_sub = df_sub.sort_values(by=by, ascending=self._ascending)
            out = np.asarray(df_sub.index)
        return out

    def copy(self) -> ComposableSorter:
        return self.__class__(self._columns.copy(), self._ascending)

    def compose(self, column: int):
        """Compose the sorter object."""
        new = self.copy()
        new._columns.add(column)
        return new

    def decompose(self, column: int):
        """Decompose the filter object."""
        new = self.copy()
        new._columns.remove(column)
        return new

    def switch(self) -> ComposableSorter:
        """New sorter with the reverse order."""
        return self.__class__(self._columns, not self._ascending)

    def is_identity(self) -> bool:
        """True if the sorter is the identity sorter."""
        return len(self._columns) == 0
