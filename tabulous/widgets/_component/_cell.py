from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Mapping,
    SupportsIndex,
    Tuple,
    Any,
    Iterator,
)
import warnings

from qtpy import QtGui
from qtpy.QtCore import Qt

from tabulous.exceptions import TableImmutableError
from tabulous.types import EvalInfo
from tabulous.color import ColorTuple
from tabulous._psygnal import InCellRangedSlot
from ._base import TableComponent
from tabulous.widgets._registry import SupportActionRegistration

if TYPE_CHECKING:
    import pandas as pd
    from tabulous.widgets import TableBase  # noqa: F401


class _Sequence2D(TableComponent):
    def __getitem__(self, key: tuple[int, int]):
        raise NotImplementedError()

    def _assert_integers(self, key: tuple[int, int]):
        r, c = key
        if not (isinstance(r, SupportsIndex) and isinstance(c, SupportsIndex)):
            raise TypeError("Cell label must be accessed by integer indices.")


class CellLabelInterface(_Sequence2D):
    def __getitem__(self, key: tuple[int, int]) -> str | None:
        """Get the label of a cell."""
        self._assert_integers(key)
        return self.parent.native.itemLabel(*key)

    def __setitem__(self, key: tuple[int, int], value: str):
        """Set the label of a cell."""
        self._assert_integers(key)
        return self.parent.native.setItemLabel(*key, value)

    def __delitem__(self, key: tuple[int, int]):
        """Delete the label of a cell."""
        self._assert_integers(key)
        return self.parent.native.setItemLabel(*key, None)


class CellReferenceInterface(
    TableComponent, Mapping[Tuple[int, int], InCellRangedSlot]
):
    """Interface to the cell references of a table."""

    def _table_map(self):
        return self.parent._qwidget._qtable_view._table_map

    def __getitem__(self, key: tuple[int, int]):
        return self._table_map()[key]

    def __iter__(self) -> Iterator[InCellRangedSlot]:
        return iter(self._table_map())

    def __len__(self) -> int:
        return len(self._table_map())

    def __repr__(self) -> str:
        slots = self._table_map()
        cname = type(self).__name__
        if len(slots) == 0:
            return f"{cname}()"
        s = ",\n\t".join(f"{k}: {slot!r}" for k, slot in slots.items())
        return f"{cname}(\n\t{s}\n)"


class CellBackgroundColorInterface(_Sequence2D):
    def __getitem__(self, key: tuple[int, int]) -> ColorTuple | None:
        """Get the background color of a cell."""
        self._assert_integers(key)
        model = self.parent.native.model()
        idx = model.index(*key)
        qcolor = model.data(idx, role=Qt.ItemDataRole.BackgroundRole)
        if isinstance(qcolor, QtGui.QColor):
            return ColorTuple(*qcolor.getRgb())
        return None


class CellForegroundColorInterface(_Sequence2D):
    def __getitem__(self, key: tuple[int, int]) -> ColorTuple | None:
        """Get the text color of a cell."""
        self._assert_integers(key)
        model = self.parent.native.model()
        idx = model.index(*key)
        qcolor = model.data(idx, role=Qt.ItemDataRole.TextColorRole)
        if isinstance(qcolor, QtGui.QColor):
            return ColorTuple(*qcolor.getRgb())
        return None


class CellDisplayedTextInterface(_Sequence2D):
    def __getitem__(self, key: tuple[int, int]) -> str:
        """Get the displayed text of a cell."""
        self._assert_integers(key)
        model = self.parent.native.model()
        idx = model.index(*key)
        return model.data(idx, role=Qt.ItemDataRole.DisplayRole)


class CellInterface(TableComponent, SupportActionRegistration["TableBase", int]):
    """
    Interface with table cells.

    This object can be used to emulate editing cells in the table.

    >>> table.cell[i, j]  # get the (i, j) cell value shown in the table
    >>> table.cell[i, j] = value  # set the (i, j) cell value
    >>> table.cell[i, j] = "&=np.mean(df.iloc[:, 0]"  # in-cell evaluation
    >>> del table.cell[i, j]  # delete the (i, j) cell value

    Label texts in the cell can be accessed by the ``label`` attribute.

    >>> table.cell.label[i, j]  # get the (i, j) cell label text
    >>> table.cell.label[i, j] = value  # set the (i, j) cell label text
    >>> del table.cell.label[i, j]  # delete the (i, j) cell label text

    Use ``register`` to register a contextmenu function.

    >>> @table.cell.register("My Action")
    >>> def my_action(table, index):
    ...     # do something
    """

    def __getitem__(self, key: tuple[int | slice, int | slice]):
        return self.parent._qwidget.model().df.iloc[key]

    def __setitem__(self, key: tuple[int | slice, int | slice], value: Any) -> None:
        table = self.parent
        if not table.editable:
            raise TableImmutableError("Table is not editable.")

        import pandas as pd
        from tabulous._qt._table._base._line_edit import QCellLiteralEdit

        row, col = self._normalize_key(key)

        if isinstance(value, str) and QCellLiteralEdit._is_eval_like(value):
            if row.stop - row.start == 1 and col.stop - col.start == 1:
                expr, is_ref = QCellLiteralEdit._parse_ref(value)
                _r0, _c0 = row.start, col.start
                _r1 = table.proxy._get_proxy_object().get_source_index(_r0)
                _c1 = table.columns.filter._get_filter().get_source_index(_c0)
                info = EvalInfo(
                    pos=(_r0, _c0),
                    source_pos=(_r1, _c1),
                    expr=expr,
                    is_ref=is_ref,
                )
                table.events.evaluated.emit(info)
                return None
            else:
                raise ValueError("Cannot evaluate a multi-cell selection.")

        if isinstance(value, str) or not hasattr(value, "__iter__"):
            _value = [[value]]
        else:
            _value = value
        try:
            df = pd.DataFrame(_value)
        except ValueError:
            raise ValueError(f"Could not convert value {_value!r} to DataFrame.")

        if 1 in df.shape and (col.stop - col.start, row.stop - row.start) == df.shape:
            # it is natural to set an 1-D array without thinking of the direction.
            df = df.T

        table._qwidget.setDataFrameValue(row, col, df)
        return None

    def __delitem__(self, key: tuple[int | slice, int | slice]) -> None:
        """Deleting cell, equivalent to pushing Delete key."""

        table = self.parent
        if not table.editable:
            raise TableImmutableError("Table is not editable.")
        row, col = key
        table._qwidget.setSelections([(row, col)])
        table._qwidget.deleteValues()
        return None

    def _normalize_key(
        self,
        key: tuple[int | slice, int | slice],
    ) -> tuple[slice, slice]:
        if len(key) == 1:
            key = (key, slice(None))
        row, col = key

        if isinstance(row, slice):
            row = _normalize_slice(row, self.parent._qwidget.model().df.shape[0])
        else:
            row = slice(row, row + 1)

        if isinstance(col, slice):
            col = _normalize_slice(col, self.parent._qwidget.model().df.shape[1])
        else:
            col = slice(col, col + 1)
        return row, col

    @property
    def _qcontextmenu(self):
        """The QContextMenu widget."""
        return self.parent.native._qt_context_menu

    def _get_qregistry(self):
        return self.parent.native

    label = CellLabelInterface()
    ref = CellReferenceInterface()
    text_color = CellForegroundColorInterface()
    background_color = CellBackgroundColorInterface()
    text = CellDisplayedTextInterface()

    def selected_at(self, r: int, c: int) -> bool:
        """Check if a cell is selected."""
        for rr, cc in self.parent.selections:
            if rr.start <= r < rr.stop and cc.start <= c < cc.stop:
                return True
        return False

    def get_label(self, r: int, c: int) -> str | None:
        """Get the label of a cell."""
        warnings.warn(
            "get_label is deprecated. Use `table.cell.label[r, c]` instead.",
            DeprecationWarning,
        )
        return self.label[r, c]

    def set_label(self, r: int, c: int, text: str):
        """Set the label of a cell."""
        warnings.warn(
            f"set_label is deprecated. Use `table.cell.label[r, c] = {text!r}` "
            "instead.",
            DeprecationWarning,
        )
        self.label[r, c] = text

    def set_labeled_data(
        self,
        r: int,
        c: int,
        data: dict[str, Any] | pd.Series | tuple,
        sep: str = "",
    ):
        """
        Set given data with cell labels.

        Parameters
        ----------
        r : int
            Starting row index.
        c : int
            Starting column index.
        data : dict[str, Any], pd.Series or (named) tuple
            Data to be set.
        sep : str, optional
            Separator added at the end of labels.
        """
        import pandas as pd

        ndata = len(data)
        if isinstance(data, dict):
            _data = pd.Series(data)
        elif isinstance(data, tuple):
            index = getattr(data, "_fields", range(ndata))
            _data = pd.Series(data, index=index)
        elif isinstance(data, pd.Series):
            _data = data.copy()
        else:
            raise TypeError(f"Cannot convert {data!r} to Series.")

        if sep:
            _data.index = [f"{idx}{sep}" for idx in _data.index]

        self.parent._qwidget.setLabeledData(slice(r, r + ndata), slice(c, c + 1), _data)
        return None


def _normalize_slice(sl: slice, size: int) -> slice:
    start = sl.start
    stop = sl.stop

    if sl.step not in (None, 1):
        raise ValueError("Row slice step must be 1.")

    if start is None:
        start = 0
    elif start < 0:
        start = size + start
    if stop is None:
        stop = size
    elif stop < 0:
        stop = size + stop
    return slice(start, stop)
