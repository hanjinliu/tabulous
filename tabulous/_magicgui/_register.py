from __future__ import annotations
from typing import Any, Callable, Iterable, TYPE_CHECKING, cast
from qtpy import QtWidgets as QtW
from magicgui import register_type

from magicgui.widgets import (
    Widget,
    Container,
    ComboBox,
    Label,
)
from tabulous.widgets import (
    TableViewerBase,
    TableBase,
    Table,
    SpreadSheet,
)
from tabulous.types import (
    TableColumn,
    TableData,
    TableDataTuple,
    TableInfoInstance,
)

if TYPE_CHECKING:
    import pandas as pd
    from magicgui.widgets import FunctionGui

_DEFAULT_NAME = "Result"


def find_table_viewer_ancestor(widget: Widget | QtW.QWidget) -> TableViewerBase | None:
    from tabulous._qt._mainwindow import _QtMainWidgetBase

    if isinstance(widget, Widget):
        qwidget = widget.native
    elif isinstance(widget, QtW.QWidget):
        qwidget = widget
    else:
        raise TypeError(f"Cannot use {type(widget)} as an input.")
    qwidget: QtW.QWidget
    while True:
        if isinstance(qwidget, _QtMainWidgetBase):
            qwidget = cast(_QtMainWidgetBase, qwidget)
            return qwidget._table_viewer
        qwidget = qwidget.parent()
        if qwidget is None:
            return None


def find_current_table(widget: Widget | QtW.QWidget) -> TableBase | None:
    viewer = find_table_viewer_ancestor(widget)
    if viewer is None:
        return None
    table = viewer.current_table
    if table is None:
        return None
    return table


def get_any_tables(widget: Widget) -> list[tuple[str, Any]]:
    """Get the list of available tables and the names."""
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return [(t.name, t) for t in v.tables]


def get_tables(widget: Widget) -> list[tuple[str, Any]]:
    """Get the list of available tables and the names."""
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return [(t.name, t) for t in v.tables if isinstance(t, Table)]


def get_spreasheets(widget: Widget) -> list[tuple[str, Any]]:
    """Get the list of available table data and the names."""
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return [(t.name, t) for t in v.tables if isinstance(t, SpreadSheet)]


def get_table_data(widget: Widget) -> list[tuple[str, Any]]:
    """Get the list of available table data and the names."""
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return [(table.name, table.data) for table in v.tables]


def open_viewer(gui, result: TableViewerBase, return_type: type):
    return result.show()


def add_table_to_viewer(
    gui: FunctionGui,
    result: Any,
    return_type: type,
) -> None:
    viewer = find_table_viewer_ancestor(gui)
    if viewer is None:
        return
    viewer.add_layer(result, update=True)


def add_table_data_to_viewer(gui: FunctionGui, result: Any, return_type: type) -> None:
    viewer = find_table_viewer_ancestor(gui)
    if viewer is None:
        return

    from pandas.core.groupby.generic import DataFrameGroupBy

    if isinstance(result, DataFrameGroupBy):
        viewer.add_groupby(result, name=f"{gui.name}-{_DEFAULT_NAME}", update=True)
    else:
        viewer.add_table(result, name=f"{gui.name}-{_DEFAULT_NAME}", update=True)


def add_table_data_tuple_to_viewer(
    gui: FunctionGui,
    result: tuple,
    return_type: type,
):
    viewer = find_table_viewer_ancestor(gui)
    if viewer is None:
        return
    n = len(result)
    if n == 1:
        data = (result[0], f"{gui.name}-{_DEFAULT_NAME}", {})
    elif n == 2:
        if isinstance(result[1], dict):
            name = result[1].pop("name", f"{gui.name}-{_DEFAULT_NAME}")
            data = (result[0], name, result[1])
        else:
            data = (result[0], result[1], {})
    elif n == 3:
        data = result
    else:
        raise ValueError(f"Length of TableDataTuple must be < 4, got {n}.")
    viewer.add_table(data[0], name=data[1], **data[2], update=True)


register_type(
    TableViewerBase,
    return_callback=open_viewer,
    bind=find_table_viewer_ancestor,
)
register_type(TableBase, return_callback=add_table_to_viewer, choices=get_any_tables)
register_type(Table, return_callback=add_table_to_viewer, choices=get_tables)
register_type(SpreadSheet, return_callback=add_table_to_viewer, choices=get_spreasheets)
register_type(
    TableData,
    return_callback=add_table_data_to_viewer,
    choices=get_table_data,
    nullable=False,
)
register_type(TableDataTuple, return_callback=add_table_data_tuple_to_viewer)

# Widget
class ColumnChoice(Container):
    def __init__(
        self,
        data_choices: Iterable[pd.DataFrame]
        | Callable[[Widget], Iterable[pd.DataFrame]],
        value=None,
        **kwargs,
    ):
        self._dataframe_choices = ComboBox(choices=data_choices, value=value, **kwargs)
        self._column_choices = ComboBox(choices=self._get_available_columns)
        _label_l = Label(value='["')
        _label_l.max_width = 24
        _label_r = Label(value='"]')
        _label_r.max_width = 24
        super().__init__(
            layout="horizontal",
            widgets=[self._dataframe_choices, _label_l, self._column_choices, _label_r],
            labels=False,
            name=kwargs.get("name"),
        )
        self.margins = (0, 0, 0, 0)
        self._dataframe_choices.changed.connect(self._set_available_columns)

    def _get_available_columns(self, w=None):
        df: pd.DataFrame = self._dataframe_choices.value
        cols = getattr(df, "columns", [])
        return cols

    def _set_available_columns(self, w=None):
        cols = self._get_available_columns()
        self._column_choices.choices = cols
        return None

    @property
    def value(self) -> pd.Series:
        df = self._dataframe_choices.value
        return df[self._column_choices.value]


register_type(
    TableColumn,
    widget_type=ColumnChoice,
    return_callback=add_table_data_to_viewer,
    data_choices=get_table_data,
    nullable=False,
)


class ColumnNameChoice(Container):
    """
    A container widget with a DataFrame selection and multiple column name selections.

    This widget is composed of two or more ComboBox widgets. The top one is to choose a
    DataFrame and the rest are to choose column names from the DataFrame. When the
    DataFrame selection changed, the column name selections will also changed
    accordingly.
    """

    def __init__(
        self,
        data_choices: Iterable[pd.DataFrame]
        | Callable[[Widget], Iterable[pd.DataFrame]],
        column_choice_names: Iterable[str],
        value=None,
        **kwargs,
    ):
        self._dataframe_choices = ComboBox(choices=data_choices, value=value, **kwargs)
        self._column_names: list[ComboBox] = []
        for cn in column_choice_names:
            self._column_names.append(
                ComboBox(choices=self._get_available_columns, name=cn, nullable=True)
            )
        self._child_container = Container(widgets=self._column_names, layout="vertical")
        self._child_container.margins = (0, 0, 0, 0)
        super().__init__(
            layout="vertical",
            widgets=[self._dataframe_choices, self._child_container],
            labels=False,
            name=kwargs.get("name"),
        )
        self.margins = (0, 0, 0, 0)
        self._dataframe_choices.changed.connect(self._set_available_columns)

    def _get_available_columns(self, w=None):
        df: pd.DataFrame = self._dataframe_choices.value
        cols = getattr(df, "columns", [])
        return cols

    def _set_available_columns(self, w=None):
        cols = self._get_available_columns()
        for cbox in self._column_names:
            cbox.choices = cols
        return None

    @property
    def value(self) -> tuple[pd.DataFrame, list[str]]:
        df = self._dataframe_choices.value
        colnames = [cbox.value for cbox in self._column_names]
        return (df, colnames)


register_type(
    TableInfoInstance, widget_type=ColumnNameChoice, data_choices=get_table_data
)
