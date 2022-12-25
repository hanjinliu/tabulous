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
        self._proxy_type = "none"

    @property
    def proxy_type(self) -> str:
        return self._proxy_type

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply the proxy rule to the dataframe."""
        sl = self._obj
        if sl is None:
            return df
        if callable(sl):
            sl_filt = sl(df)
        else:
            sl_filt = sl
        if sl_filt.dtype.kind == "b":
            df_filt = df[sl_filt]
            self._proxy_type = "filter"
        elif sl_filt.dtype.kind in "ui":
            df_filt = df.iloc[sl_filt]
            self._proxy_type = "sort"
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
            elif sl.dtype.kind in "ui":
                r0 = sl[r]
        return r0
