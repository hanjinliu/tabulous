from __future__ import annotations
from typing import (
    TYPE_CHECKING,
    Sequence,
    overload,
    Any,
    Callable,
)

import numpy as np
from tabulous.types import ProxyType
from ._base import TableComponent

if TYPE_CHECKING:
    from numpy.typing import NDArray
    import pandas as pd
    from tabulous.widgets._table import TableBase

    _SortArray = NDArray[np.integer]
    _FilterArray = NDArray[np.bool_]


class ProxyInterface(TableComponent):
    """Interface to the table sorting/filtering."""

    @overload
    def sort(self, by: str | Sequence[str], ascending: bool = True) -> None:
        ...

    @overload
    def sort(self, func: Callable[[pd.DataFrame], _SortArray]) -> None:
        ...

    def sort(self, by, ascending: bool = True) -> None:
        """
        Apply sort proxy to the table.

        If column names are given, sort button(s) will be added to the header.
        """
        if callable(by):
            sort_func = self._get_sort_function(by, ascending)
            return self.parent.proxy.set(sort_func)

        from tabulous._qt._proxy_button import QHeaderSortButton

        if isinstance(by, str):
            by = [by]
        QHeaderSortButton.from_table(self.parent, by, ascending=ascending)
        return None

    def _get_sort_function(
        self,
        by: str | Sequence[str] | Callable[[pd.DataFrame], _SortArray],
        ascending: bool = True,
    ) -> Callable[[pd.DataFrame], _SortArray]:
        if callable(by):
            if not ascending:
                raise TypeError("Cannot sort by a callable in descending order.")

            def _sort(df: pd.DataFrame) -> _SortArray:
                arr = np.asarray(by(df))
                if arr.ndim != 1:
                    raise TypeError("The callable must return a 1D array.")
                elif arr.dtype.kind not in "ui":
                    raise TypeError("The callable must return an integer array.")
                return arr

        else:
            if not isinstance(by, str) and len(by) == 1:
                by = by[0]

            if isinstance(by, str):

                def _sort(df: pd.DataFrame) -> _SortArray:
                    out = np.asarray(df[by].argsort())
                    if not ascending:
                        out = out[::-1]
                    return out

            elif isinstance(by, Sequence):
                by = list(by)

                def _sort(df: pd.DataFrame) -> _SortArray:
                    df_sub = df[by]
                    nr = len(df_sub)
                    df_sub.index = range(nr)
                    df_sub = df_sub.sort_values(by=by, ascending=ascending)
                    return np.asarray(df_sub.index)

            else:
                raise TypeError(
                    "The `by` argument must be a column name or a sequence of it."
                )

            _sort.__name__ = f"sort<by={by!r}, ascending={ascending}>"
        return _sort

    @overload
    def filter(self, expr: str, namespace: dict = {}) -> None:
        ...

    @overload
    def filter(self, func: Callable[[pd.DataFrame], _FilterArray]) -> None:
        ...

    def filter(self, expr: str, namespace: dict = {}) -> None:
        """Apply filter proxy to the table."""
        if callable(expr):
            func = expr
            if namespace:
                raise TypeError("Cannot use a namespace with a callable.")

            def _filter(df: pd.DataFrame) -> _FilterArray:
                arr = np.asarray(func(df))
                if arr.ndim != 1:
                    raise TypeError("The callable must return a 1D array.")
                elif arr.dtype.kind != "b":
                    raise TypeError("The callable must return a boolean array.")
                return arr

        else:

            def _filter(df: pd.DataFrame) -> np.ndarray:
                ns = dict(**dict(df.items()), **namespace)
                return eval(expr, ns, {})

            _filter.__name__ = f"filter<{expr!r}>"

        self.parent._qwidget.setProxy(_filter)
        return None

    def show_filter_button(self, columns: str | list[str]):
        from tabulous._qt._proxy_button import QHeaderFilterButton

        table = self.parent
        if isinstance(columns, str):
            columns = [columns]
        QHeaderFilterButton.from_table(table, columns, show_menu=False)
        return None

    def reset(self) -> None:
        """Reset filter or sort."""
        return self._set_value(None)

    def set(self, proxy: ProxyType) -> None:
        """Set filter or sort."""
        return self._set_value(proxy)

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply the current proxy to the DataFrame."""
        return self._get_proxy_object().apply(df)

    def as_indexer(self) -> np.ndarray:
        """Return the indexer that represents the current proxy."""
        return self._get_proxy_object().as_indexer(self.parent.data)

    @property
    def proxy_type(self):
        """Return the current proxy type."""
        return self._get_proxy_object().proxy_type

    def _set_value(self, value: Any):
        return self.parent._qwidget.setProxy(value)

    def __set__(self, obj: TableBase, value: ProxyType):
        return super().__set__(obj, value)

    def _get_proxy_object(self):
        """Return the current proxy function."""
        return self.parent._qwidget._proxy
