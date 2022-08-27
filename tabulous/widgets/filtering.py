from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable
import operator as op

from ..types import FilterType

if TYPE_CHECKING:
    from ._table import TableBase
    import pandas as pd


class FilterProxy:
    """
    A proxy of column-based DataFrame filtering.

    This object makes filtering of table easier. For instance, to filter a table
    by a column, you can do:
    >>> table.filter["a"] < 5
    which is equivalent to
    >>> table.filter = lambda df: df["a"] < 5
    """

    def __init__(self, table: TableBase | None = None):
        self._table = table

    def __repr__(self) -> str:
        return f"{type(self).__name__}(table={self._table!r}, func={self.func!r})"

    def __bool__(self) -> bool:
        return self.func is not None

    def __get__(self, obj: TableBase | None, type=None):
        return self.__class__(obj)

    def __set__(self, obj: TableBase | None, value: FilterType):
        if obj is None:
            return None
        data = obj.data
        if callable(value):
            # dry run
            try:
                df = data.head(3)
                filt = value(df)
            except Exception as e:
                raise ValueError(
                    f"Dry run failed with filter function {value} due to following error:\n"
                    f"{type(e).__name__}: {e}"
                ) from None

        elif isinstance(value, FilterProxy):
            value = value.func
        elif value is not None and len(value) != data.shape[0]:
            raise ValueError(
                f"Shape mismatch between data {data.shape} and input slice {len(value)}."
            )
        obj._qwidget.setFilter(value)

    def __delete__(self, obj: TableBase):
        """Disable filter."""
        obj.filter = None

    def __getitem__(self, key):
        return FilterIndexer(self._table, key)

    @property
    def func(self) -> FilterType:
        """Get the filter function."""
        return self._table._qwidget.filter()

    @property
    def table(self) -> TableBase | None:
        """Return the connected table."""
        return self._table

    def array(self) -> pd.Series:
        f = self.func
        if callable(f):
            arr = f(self._table.data)
        else:
            arr = f
        return arr


class _Void:
    """Private void type."""


_void = _Void()


class FilterIndexer:
    def __init__(
        self,
        table: TableBase,
        key: Any,
        *,
        current_filter: ColumnFilter | None | _Void = _void,
    ):
        self._table = table
        self._key = key
        self._filter = current_filter
        if current_filter is not _void:
            self._table._qwidget.setFilter(current_filter)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} of {self._table!r} at column {self._key!r}>"

    def chain(self, other: ColumnFilter) -> ColumnFilter:
        if self._filter is _void or self._filter is None:
            fil = other
        else:
            fil = self._filter & other
        return self.filter(fil)

    def filter(self, filter: ColumnFilter) -> FilterIndexer:
        return FilterIndexer(self._table, self._key, current_filter=filter)

    def __eq__(self, other) -> ColumnFilter:
        fil = ColumnFilter.from_operator("__eq__", self._key, other)
        return self.chain(fil)

    def __gt__(self, other) -> ColumnFilter:
        fil = ColumnFilter.from_operator("__gt__", self._key, other)
        return self.chain(fil)

    def __ge__(self, other) -> ColumnFilter:
        fil = ColumnFilter.from_operator("__ge__", self._key, other)
        return self.chain(fil)

    def __lt__(self, other) -> ColumnFilter:
        fil = ColumnFilter.from_operator("__lt__", self._key, other)
        return self.chain(fil)

    def __le__(self, other) -> ColumnFilter:
        fil = ColumnFilter.from_operator("__le__", self._key, other)
        return self.chain(fil)

    def __ne__(self, other) -> ColumnFilter:
        fil = ColumnFilter.from_operator("__ne__", self._key, other)
        return self.chain(fil)

    def __and__(self, other: FilterIndexer) -> FilterIndexer:
        fil = self._filter & other._filter
        return self.filter(fil)

    def __or__(self, other: FilterIndexer) -> FilterIndexer:
        fil = self._filter | other._filter
        return self.filter(fil)

    def __contains__(self, other) -> None:
        fil = ColumnFilter(
            lambda df: df[self._key].isin(other),
            repr=f"df[{self._key}].isin({list(other)!r})",
        )
        return self.chain(fil)

    # TODO: __invert__, __mod__


class ColumnFilter:
    """A callable object compatible with DataFrame filter, specific to column based filter."""

    def __init__(
        self,
        func: Callable[[pd.DataFrame], pd.Series],
        repr: str | None = None,
    ):
        self._func = func
        self._repr = repr

    def __call__(self, df: pd.DataFrame) -> pd.Series:
        series = self._func(df)
        if self._repr is not None:
            series.name = self._repr
        return series

    def __repr__(self) -> str:
        return f"<{type(self).__name__} of {self._repr}>"

    def __and__(self, other: ColumnFilter) -> ColumnFilter:
        return ColumnFilter(
            lambda df: self(df) & other(df),
            repr=f"{self._repr} & {other._repr}",
        )

    def __or__(self, other: ColumnFilter) -> ColumnFilter:
        return ColumnFilter(
            lambda df: self(df) | other(df),
            repr=f"{self._repr} | {other._repr}",
        )

    @classmethod
    def from_operator(self, operator_name: str, key: Any, other: Any) -> ColumnFilter:
        """
        Construct an instance from a operator.

        Parameters
        ----------
        operator_name : str
            Name of operator, such as "__eq__".
        key : Any
            Target column name.
        other : Any
            The other argument of the operator.

        Returns
        -------
        ColumnFilter
            An instance initialized with the given operator.
        """
        f = getattr(op, operator_name)
        _op_ = OPERATORS[operator_name]
        return ColumnFilter(
            lambda df: f(df[key], other),
            repr=f"df[{key!r}] {_op_} {other!r}",
        )


OPERATORS = {
    "__eq__": "==",
    "__gt__": ">",
    "__ge__": ">=",
    "__lt__": "<",
    "__le__": "<=",
    "__ne__": "!=",
}
