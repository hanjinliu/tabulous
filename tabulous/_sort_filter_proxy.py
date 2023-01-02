from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Callable, NamedTuple
import numpy as np
from enum import Enum
from tabulous.types import ProxyType
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
        self._obj: ProxyType | None = obj
        if self._obj is None:
            self._proxy_type = ProxyTypes.none
        else:
            self._proxy_type = ProxyTypes.unknown

    def __repr__(self) -> str:
        cname = type(self).__name__
        return f"{cname}<proxy_type={self.proxy_type}, obj={self._obj!r}>"

    @property
    def proxy_type(self) -> ProxyTypes:
        """The proxy type."""
        return self._proxy_type

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
        if callable(sl):
            if ref is None:
                ref_input = df
            elif callable(ref):
                ref_input = ref()
            sl_filt = sl(ref_input)
        else:
            sl_filt = sl
        if sl_filt.dtype.kind == "b":
            df_filt = df[sl_filt]
            self._proxy_type = ProxyTypes.filter
        elif sl_filt.dtype.kind in "ui":
            df_filt = df.iloc[sl_filt]
            self._proxy_type = ProxyTypes.sort
        else:
            raise TypeError(f"Invalid filter type: {sl_filt.dtype}")
        return df_filt

    def get_source_index(self, r: int, df: pd.DataFrame) -> int:
        """Get the source index of the row in the dataframe."""
        sl = self._obj
        if sl is None:
            r0 = r
        else:
            if callable(sl):
                sl = sl(df)
            else:
                sl = sl

            if sl.dtype.kind == "b":
                r0 = np.where(sl)[0][r]
                self._proxy_type = ProxyTypes.filter
            elif sl.dtype.kind in "ui":
                r0 = sl[r]
                self._proxy_type = ProxyTypes.sort
            else:
                raise TypeError(f"Invalid filter type: {sl.dtype}")
        return r0

    def as_indexer(self, df: pd.DataFrame) -> np.ndarray | slice:
        sl = self._obj
        if sl is None:
            return slice(None)
        if callable(sl):
            sl_filt = sl(df)
        else:
            sl_filt = sl
        return sl_filt


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
    isin = "contains"
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

    def compose(self, type: FilterType, column: int, arg: Any) -> ComposableFilter:
        """Compose with an additional column filter."""
        if type is FilterType.none:
            return self
        new = self.copy()
        new._dict[column] = FilterInfo(FilterType(type), arg)
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
