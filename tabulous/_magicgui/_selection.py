from __future__ import annotations
from typing import Any

from magicgui import register_type
from magicgui.widgets import (
    Container,
    PushButton,
    LineEdit,
)

from tabulous.widgets import TableBase, SpreadSheet
from tabulous._selection_op import (
    SelectionOperator,
    ILocSelOp,
    parse,
    construct,
)

from ._register import find_current_table


class SelectionWidget(Container):
    """A container widget for a table selection."""

    def __init__(
        self,
        value: Any = None,
        nullable=False,
        format: str = "iloc",
        allow_out_of_bounds: bool = False,
        **kwargs,
    ):
        self._line = LineEdit(tooltip="Selection string (e.g. 'df.iloc[2:4, 3:]')")
        self._btn = PushButton(
            text="Read selection", tooltip="Read current table selection."
        )
        super().__init__(layout="horizontal", widgets=[self._line, self._btn], **kwargs)
        self.margins = (0, 0, 0, 0)
        self._line.changed.disconnect()
        self._btn.changed.disconnect()
        self._line.changed.connect(self.changed.emit(self._line.value))
        self._btn.changed.connect(lambda: self._read_selection())

        self._format = format
        self._allow_out_of_bounds = allow_out_of_bounds

        if isinstance(value, (str, SelectionOperator, tuple)):
            self.value = value

    @property
    def value(self) -> SelectionOperator | None:
        """Get selection operator that represents current selection."""
        text = self._line.value
        if text:
            return parse(text, df_expr="df")
        return None

    @value.setter
    def value(self, val: str | SelectionOperator) -> None:
        if isinstance(val, str):
            if val:
                text = parse(val, df_expr="df").fmt()
            else:
                text = ""
        elif isinstance(val, SelectionOperator):
            text = val.fmt()
        elif isinstance(val, tuple):
            text = ILocSelOp(*val).fmt()
        elif val is None:
            text = ""
        else:
            raise TypeError(f"Invalid type for value: {type(val)}")
        self._line.value = text
        return None

    @property
    def format(self) -> str:
        return self._format

    def _find_table(self) -> TableBase:
        table = find_current_table(self)
        if table is None:
            raise ValueError("No table found.")
        return table

    def _read_selection(self, table: TableBase | None = None):
        if table is None:
            table = self._find_table()

        sels = table.selections
        if len(sels) > 1:
            raise ValueError("More than one selection is given.")
        sel = sels[0]

        qwidget = table.native
        column_selected = qwidget._qtable_view._selection_model._col_selection_indices
        if isinstance(table, SpreadSheet):
            df = table.native._data_raw
        else:
            df = table.data_shown
        _selop = construct(
            *sel,
            df,
            method=self.format,
            column_selected=column_selected,
            allow_out_of_bounds=self._allow_out_of_bounds,
        )
        self._line.value = _selop.fmt()
        self.changed.emit(_selop)
        return None


register_type(SelectionOperator, widget_type=SelectionWidget)
