from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np
from tabulous.types import ProxyType

if TYPE_CHECKING:
    import pandas as pd


class SortFilterProxy:
    """A custom sort/filter proxy for pandas dataframes."""

    def __init__(self, obj: ProxyType | None = None):
        if isinstance(obj, SortFilterProxy):
            obj = obj._obj
        self._obj = obj
        self._is_filter = False
        self._is_sort = False

    @property
    def proxy_type(self) -> str:
        if self._is_filter:
            return "filter"
        elif self._is_sort:
            return "sort"
        else:
            return "none"

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        sl = self._obj
        if sl is None:
            return df
        if callable(sl):
            sl_filt = sl(df)
        else:
            sl_filt = sl
        if sl_filt.dtype.kind == "b":
            df_filt = df[sl_filt]
            self._is_filter = True
            self._is_sort = False
        elif sl_filt.dtype.kind in "ui":
            df_filt = df.iloc[sl_filt]
            self._is_filter = False
            self._is_sort = True
        else:
            raise TypeError(f"Invalid filter type: {sl_filt.dtype}")
        return df_filt

    def get_source_index(self, r: int, df: pd.DataFrame) -> int:
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
            elif sl.dtype.kind in "ui":
                r0 = sl[r]
        return r0
