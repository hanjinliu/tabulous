from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, TypeVar, Union, overload, Callable

import numpy as np

from tabulous.types import ColorMapping
from ._base import TableComponent
from ._column_setting import _Void

if TYPE_CHECKING:
    from numpy.typing import NDArray
    import pandas as pd
    from tabulous.widgets import TableBase
    from ._column_setting import (
        _Interpolatable,
        _ColormapInterface,
        _DictPropertyInterface,
    )

    _RowLocIdx = Union[int, str, slice, list[str], list[int]]
    _ColumnLocIdx = Union[str, slice, list[str]]
    _ILocIdx = Union[slice, list[int], NDArray[np.integer]]


class TableLocIndexer(TableComponent):
    """
    loc indexer for Table widget.

    >>> sheet = viewer.add_spreadsheet(np.zeros((10, 5)))
    >>> sheet.loc[:, "B":"C"].data
    """

    # fmt: off
    @overload
    def __getitem__(self, key: _RowLocIdx | tuple[_RowLocIdx, _ColumnLocIdx]) -> TableSubset: ...  # noqa: E501
    @overload
    def __getitem__(self, key: tuple[_RowLocIdx, str]) -> TableSeries: ...
    # fmt: on

    def __getitem__(self, key):
        table = self.parent
        if not isinstance(key, tuple):
            ckey = list(self.parent.columns)
            rkey = key
        else:
            rkey, ckey = key

        if isinstance(rkey, (int, str)):
            idx = table.index.get_loc(rkey)
            rsl = slice(idx, idx + 1)
        elif isinstance(rkey, slice):
            if rkey.start is None:
                start = None
            else:
                start = table.index.get_loc(rkey.start)
            if rkey.stop is None:
                stop = None
            else:
                stop = table.index.get_loc(rkey.stop) + 1
            rsl = slice(start, stop)
        elif isinstance(rkey, Sequence):
            rsl = [table.index.get_loc(lbl) for lbl in rkey]
        else:
            raise TypeError(f"Cannot loc-slice by {type(ckey)}")

        if isinstance(ckey, str):
            if ckey not in table.columns:
                raise KeyError(ckey)
            return TableSeries(table, rsl, ckey)
        elif isinstance(ckey, slice):
            if ckey.start is None:
                start = None
            else:
                start = table.columns.get_loc(ckey.start)
            if ckey.stop is None:
                stop = None
            else:
                stop = table.columns.get_loc(ckey.stop) + 1
            csl = slice(start, stop)
            columns = table.columns[csl]
            return TableSubset(table, rsl, columns)
        elif isinstance(ckey, Sequence):
            for ck in ckey:
                if ck not in table.columns:
                    raise KeyError(ckey)
            return TableSubset(table, rsl, ckey)
        else:
            raise TypeError(f"Cannot loc-slice by {type(ckey)}")


class TableILocIndexer(TableComponent):
    """
    iloc indexer for Table widget.

    >>> sheet = viewer.add_spreadsheet(np.zeros((10, 5)))
    >>> sheet.iloc[:, 2:5].data
    """

    # fmt: off
    @overload
    def __getitem__(self, key: _ILocIdx | tuple[_ILocIdx, _ILocIdx]) -> TableSubset: ...
    @overload
    def __getitem__(self, key: tuple[_ILocIdx, int]) -> TableSeries: ...
    # fmt: on

    def __getitem__(self, key):
        table = self.parent
        if not isinstance(key, tuple):
            ckey = slice(None)
            rkey = key
        else:
            rkey, ckey = key

        if isinstance(ckey, int):
            return TableSeries(table, rkey, table.columns[ckey])
        elif isinstance(ckey, slice):
            columns = table.columns[ckey]
            return TableSubset(table, rkey, columns)
        elif isinstance(ckey, Sequence):
            return TableSubset(table, rkey, list(table.columns[ckey]))
        else:
            raise TypeError(f"Cannot iloc-slice by {type(ckey)}")


class TableSubset(TableComponent):
    def __init__(
        self, parent: TableBase, row_slice: slice | list[int], columns: list[str]
    ):
        super().__init__(parent)
        self._row_slice = row_slice
        self._columns = columns

    @property
    def data(self) -> pd.DataFrame:
        table = self.parent
        return table.native._get_sub_frame(self._columns).iloc[self._row_slice]


class TableSeries(TableComponent):
    def __init__(self, parent: TableBase, row_slice: slice | list[int], column: str):
        super().__init__(parent)
        self._row_slice = row_slice
        self._column = column

    def __repr__(self) -> str:
        return f"<TableSeries<{self._column!r}> of {self.parent!r}>"

    @property
    def data(self) -> pd.Series:
        table = self.parent
        return table.native._get_sub_frame(self._column).iloc[self._row_slice]

    @property
    def text_color(self):
        """Get the text colormap of the column."""
        self._assert_row_not_sliced()
        return PartialTextColormapInterface(self.parent, self._column)

    @text_color.setter
    def text_color(self, val) -> None:
        """Set the text colormap of the column."""
        self._assert_row_not_sliced()
        self.parent.text_color[self._column] = val
        return None

    @text_color.deleter
    def text_color(self) -> None:
        """Delete the text colormap of the column."""
        self._assert_row_not_sliced()
        del self.parent.text_color[self._column]
        return None

    @property
    def background_color(self):
        """Get the background colormap of the column."""
        self._assert_row_not_sliced()
        return PartialBackgroundColormapInterface(self.parent, self._column)

    @background_color.setter
    def background_color(self, val):
        """Set the background colormap of the column."""
        self._assert_row_not_sliced()
        self.parent.background_color[self._column] = val
        return None

    @background_color.deleter
    def background_color(self):
        """Delete the background colormap of the column."""
        self._assert_row_not_sliced()
        del self.parent.background_color[self._column]
        return None

    @property
    def formatter(self):
        self._assert_row_not_sliced()
        return PartialTextFormatterInterface(self.parent, self._column)

    @formatter.setter
    def formatter(self, val):
        self._assert_row_not_sliced()
        self.parent.formatter[self._column] = val
        return None

    @formatter.deleter
    def formatter(self):
        self._assert_row_not_sliced()
        del self.parent.formatter[self._column]
        return None

    @property
    def validator(self):
        self._assert_row_not_sliced()
        return PartialValidatorInterface(self.parent, self._column)

    @validator.setter
    def validator(self, val):
        self._assert_row_not_sliced()
        self.parent.validator[self._column] = val
        return None

    @validator.deleter
    def validator(self):
        self._assert_row_not_sliced()
        del self.parent.validator[self._column]
        return None

    def _assert_row_not_sliced(self):
        if self._row_slice == slice(None):
            return
        raise ValueError(f"{self!r} is sliced in row axis.")


_F = TypeVar("_F", bound=Callable)


class _PartialInterface(TableComponent):
    def _get_field(self) -> _DictPropertyInterface:
        raise NotImplementedError()

    def __init__(self, parent: TableBase, column: str):
        super().__init__(parent)
        self._column = column

    def __repr__(self) -> str:
        pclsname = type(self._get_field()).__name__
        item = self.item()
        if item is None:
            return f"{pclsname}<{self._column!r}>(Undefined)"
        else:
            return f"{pclsname}<{self._column!r}>({item})"

    def set(self, func: _F = _Void):
        return self._get_field().set(self._column, func)

    def reset(self):
        return self._get_field().reset(self._column)

    def item(self):
        return self._get_field().get(self._column, None)


class _PartialColormapInterface(_PartialInterface):
    def _get_field(self) -> _ColormapInterface:
        raise NotImplementedError()

    def invert(self):
        return self._get_field().invert(self._column)

    def set_opacity(self, opacity: float):
        return self._get_field().set_opacity(self._column, opacity)

    def adjust_brightness(self, factor: float):
        return self._get_field().adjust_brightness(self._column, factor)

    def set(
        self,
        colormap: ColorMapping = _Void,
        *,
        interp_from: _Interpolatable | None = None,
        infer_parser: bool = True,
        opacity: float | None = None,
    ):
        return self._get_field().set(
            self._column,
            colormap,
            interp_from=interp_from,
            infer_parser=infer_parser,
            opacity=opacity,
        )


class PartialTextColormapInterface(_PartialColormapInterface):
    def _get_field(self):
        return self.parent.text_color


class PartialBackgroundColormapInterface(_PartialColormapInterface):
    def _get_field(self):
        return self.parent.background_color


class PartialTextFormatterInterface(_PartialInterface):
    def _get_field(self):
        return self.parent.formatter


class PartialValidatorInterface(_PartialInterface):
    def _get_field(self):
        return self.parent.validator
