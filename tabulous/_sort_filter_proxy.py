from __future__ import annotations
from typing import TYPE_CHECKING, Callable
import numpy as np
from enum import Enum
from tabulous.types import ProxyType

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
