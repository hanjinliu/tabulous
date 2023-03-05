from __future__ import annotations

import builtins
from functools import wraps
import ast
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Sequence,
    overload,
    Any,
    Callable,
)

import numpy as np
from tabulous.types import ProxyType, _IntArray, _BoolArray, _IntOrBoolArray
from ._base import TableComponent
from tabulous._sort_filter_proxy import ComposableFilter, ComposableSorter

if TYPE_CHECKING:
    import pandas as pd
    from tabulous.widgets._table import TableBase


class ProxyInterface(TableComponent):
    """
    Interface to the table sorting/filtering.

    To sort table, use ``sort`` method.

    >>> table.proxy.sort('A', ascending=True)  # sort by column "A"
    >>> table.proxy.sort(['A', 'B'], ascending=True)  # sort by columns "A" and "B"

    To filter table, use ``filter`` method.

    >>> table.proxy.filter('A > 0')  # filter by column "A"
    >>> table.proxy.filter('(A > 0) & (B < 0)')  # filter by columns "A" and "B"

    To use custom proxy function, use ``set`` method. A proxy function must return
    a boolean array or an integer array of the same length as the number of rows.

    >>> table.proxy.set(my_filter_func)
    >>> @table.proxy.set
    >>> def my_filter_func(df: pd.DataFrame):
    ...     # do something

    To initialize the proxy, use ``reset`` method.

    >>> table.proxy.reset()

    """

    # fmt: off
    @overload
    def sort(self, by: str | Sequence[str], ascending: bool = True, compose: bool = False) -> None: ...  # noqa: E501
    @overload
    def sort(self, func: Callable[[pd.DataFrame], _IntArray]) -> None: ...
    # fmt: on

    def sort(self, by, ascending: bool = True, compose: bool = False) -> None:
        """
        Apply sort proxy to the table.

        If column names are given, sort button(s) will be added to the header.
        """
        table = self.parent

        if callable(by):
            if not ascending or compose:
                raise TypeError(
                    "Arguments 'ascending' and 'compose' are not supported to be "
                    "used with a callable input."
                )

            @wraps(by)
            def _sort(df: pd.DataFrame) -> _IntArray:
                arr = np.asarray(by(df))
                if arr.ndim != 1:
                    raise TypeError("The callable must return a 1D array.")
                elif arr.dtype.kind not in "ui":
                    raise TypeError("The callable must return an integer array.")
                return arr

            return table.proxy.set(_sort)

        from tabulous._qt._proxy_button import QHeaderSortButton

        if isinstance(by, str):
            by = [by]

        with table.undo_manager.merging(
            lambda cmds: f"table.proxy.sort(by={by!r}, ascending={ascending!r})"
        ):
            if not (compose and isinstance(table.proxy.obj, ComposableSorter)):
                table.proxy.reset()
            for x in by:
                index = table.columns.get_loc(x)
                QHeaderSortButton.install_to_table(
                    table.native, index, ascending=ascending
                )
        return None

    def add_sort_buttons(self, columns: str | list[str]) -> None:
        """Add sort buttons to the given column header sections."""
        return self.sort(by=columns, ascending=True, compose=False)

    # fmt: off
    @overload
    def filter(self, expr: str, namespace: dict = {}) -> None: ...
    @overload
    def filter(self, func: Callable[[pd.DataFrame], _BoolArray]) -> None: ...
    # fmt: on

    def filter(self, expr, namespace={}) -> None:
        """Apply filter proxy to the table."""
        if callable(expr):
            func = expr
            if namespace:
                raise TypeError("Cannot use a namespace with a callable.")

            def _filter(df: pd.DataFrame) -> _BoolArray:
                arr = np.asarray(func(df))
                if arr.ndim != 1:
                    raise TypeError("The callable must return a 1D array.")
                elif arr.dtype.kind != "b":
                    raise TypeError("The callable must return a boolean array.")
                return arr

        else:
            if _cfil := _try_ast_parse(expr, self.parent.columns):
                from tabulous._qt._proxy_button import QHeaderFilterButton

                index = _cfil.indices().pop()
                QHeaderFilterButton.install_to_table(self.parent.native, index)
                self.parent._qwidget._set_proxy(_cfil)
                return None

            def _filter(df: pd.DataFrame) -> np.ndarray:
                ns = dict(**dict(df.items()), **namespace)
                ns["__builtins__"] = _BUILTINS
                return eval(expr, ns, {})

            _filter.__name__ = f"filter<{expr!r}>"

        self.parent._qwidget.setProxy(_filter)
        return None

    def add_filter_buttons(
        self,
        columns: str | list[str],
        *,
        show_menu: bool = False,
    ) -> None:
        """Add filter buttons to the given column header sections."""
        from tabulous._qt._proxy_button import QHeaderFilterButton

        table = self.parent
        if isinstance(columns, str):
            columns = [columns]
        else:
            columns = list(columns)

        with table.undo_manager.merging(
            lambda cmds: f"table.proxy.add_filter_buttons({columns!r})"
        ):
            if not isinstance(table.proxy.obj, ComposableFilter):
                table.proxy.reset()
            for x in reversed(columns):
                index = table.columns.get_loc(x)
                btn = QHeaderFilterButton.install_to_table(table.native, index)
        if show_menu:
            btn.showMenu()
        return None

    def hide_buttons(
        self,
        columns: str | list[str] | None = None,
        missing_ok: bool = False,
    ) -> None:
        """Hide buttons in header sections."""
        if columns is None:
            # hide all buttons
            self.parent.native.updateHorizontalHeaderWidget({})
            return None

        if isinstance(columns, str):
            indices = [self.parent.columns.get_loc(columns)]
        else:
            indices = [self.parent.columns.get_loc(c) for c in columns]
        wdts = self.parent.native._header_widgets().copy()
        popped = [wdts.pop(index, None) for index in indices]

        if not missing_ok and None in popped:
            if isinstance(columns, str):
                raise ValueError(f"Column {columns!r} does not have a header button.")
            else:
                colnames = {columns[i] for i, x in popped if x is None}
                raise ValueError(f"Columns {colnames!r} do not have header buttons.")

        return None

    def reset(self) -> None:
        """Reset filter or sort."""
        return self._set_value(None)

    def set(self, proxy: ProxyType, check_duplicate: bool = True) -> None:
        """Set filter or sort."""
        if isinstance(proxy, (list, tuple, set)):
            proxy = np.asarray(proxy)
        if check_duplicate:
            if callable(proxy):

                @wraps(proxy)
                def _wrapped(df: pd.DataFrame) -> ProxyType:
                    out = proxy(df)
                    return _check_duplicate(out)

                _proxy = _wrapped
            elif proxy is None:
                _proxy = None
            else:
                _proxy = _check_duplicate(np.asarray(proxy))
            return self._set_value(_proxy)
        return self._set_value(proxy)

    @contextmanager
    def released(self, keep_widgets: bool = False):
        """Release the proxy in this context."""
        proxy = self.obj
        qtable = self.parent.native
        if keep_widgets:
            widgets = qtable._header_widgets().copy()
        else:
            widgets = {}
        try:
            self._set_value(None)
            yield
        finally:
            self._set_value(proxy)
            if widgets:
                qtable.updateHorizontalHeaderWidget(widgets)

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

    @property
    def obj(self) -> ProxyType | None:
        """The proxy object."""
        return self._get_proxy_object()._obj

    @property
    def is_ordered(self) -> bool:
        """Return True if the proxy does not change the order of rows"""
        return self._get_proxy_object().is_ordered

    def _set_value(self, value: Any):
        return self.parent._qwidget.setProxy(value)

    def __set__(self, obj: TableBase, value: ProxyType):
        return super().__set__(obj, value)

    def _get_proxy_object(self):
        """Return the current proxy function."""
        return self.parent._qwidget._proxy


def _check_duplicate(out: _IntOrBoolArray):
    if out.dtype.kind in "ui" and np.unique(out).size != out.size:
        raise ValueError(f"The proxy contains duplicates: {out!r}")
    return out


def _try_ast_parse(expr: str, columns: pd.Index) -> ComposableFilter | None:
    ast_body = ast.parse(expr, mode="eval").body
    if not isinstance(ast_body, ast.Compare):
        return None
    try:
        cfil = ComposableFilter.from_ast(ast_body, columns)
    except Exception:
        return None
    return cfil


# "safe" builtin functions
# fmt: off
_BUILTINS = {
    k: getattr(builtins, k)
    for k in [
        "int", "str", "float", "bool", "list", "tuple", "set", "dict", "range",
        "slice", "frozenset", "len", "abs", "min", "max", "sum", "any", "all",
        "divmod", "id", "bin", "oct", "hex", "hash", "iter", "isinstance",
        "issubclass", "ord"
    ]
}
# fmt: on
