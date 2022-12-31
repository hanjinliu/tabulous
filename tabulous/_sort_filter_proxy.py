from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Any, Callable, NamedTuple
import numpy as np
from enum import Enum
from tabulous.types import ProxyType
from functools import reduce

if TYPE_CHECKING:
    import pandas as pd


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
        self._obj = obj
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
    contains = "contains"
    startswith = "startswith"
    endswith = "endswith"
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
        return self in {cls.startswith, cls.endswith, cls.matches}

    @property
    def requires_list(self) -> bool:
        return self is FilterType.contains


_FUNCTION_MAP: dict[FilterType, Callable[[pd.Series, Any], pd.Series]] = {
    FilterType.none: lambda x, a: np.ones(len(x), dtype=bool),
    FilterType.eq: lambda x, a: x == a,
    FilterType.ne: lambda x, a: x != a,
    FilterType.gt: lambda x, a: x > a,
    FilterType.ge: lambda x, a: x >= a,
    FilterType.lt: lambda x, a: x < a,
    FilterType.le: lambda x, a: x <= a,
    FilterType.contains: lambda x, a: x.isin(a),
    FilterType.startswith: lambda x, a: x.str.startswith(a),
    FilterType.endswith: lambda x, a: x.str.endswith(a),
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
    FilterType.contains: "contains",
    FilterType.startswith: "starts with",
    FilterType.endswith: "ends with",
    FilterType.matches: ".*",
}


class FilterInfo(NamedTuple):
    type: FilterType
    arg: Any


class ComposableFilter:
    def __init__(self):
        self._dict: dict[str, FilterInfo] = {}

    def __call__(self, df: pd.DataFrame) -> pd.Series:
        series = []
        for column, (type, arg) in self._dict.items():
            fn = _FUNCTION_MAP[type]
            series.append(fn(df[column], arg))
        return reduce(lambda x, y: x & y, series)

    def copy(self) -> ComposableFilter:
        new = self.__class__()
        new._dict = self._dict.copy()
        return new

    def compose(self, type: FilterType, column: str, arg: Any) -> ComposableFilter:
        new = self.copy()
        new._dict[column] = FilterInfo(FilterType(type), arg)
        return new

    def decompose(self, column: str) -> ComposableFilter:
        new = self.copy()
        new._dict.pop(column)
        return new
