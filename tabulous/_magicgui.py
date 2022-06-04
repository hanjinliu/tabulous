from __future__ import annotations
from typing import Any, Callable, Iterable, TYPE_CHECKING
from qtpy.QtWidgets import QWidget
from magicgui import register_type
from magicgui.widgets import Widget, Container, ComboBox, Label

from .widgets import TableViewer, TableLayer
from .types import TableColumn, TableData

if TYPE_CHECKING:
    import pandas as pd

def find_table_viewer_ancestor(widget: Widget | QWidget) -> TableViewer | None:
    if isinstance(widget, Widget):
        qwidget = widget.native
    elif isinstance(widget, QWidget):
        qwidget = widget
    else:
        raise TypeError(f"Cannot use {type(widget)} as an input.")
    qwidget: QWidget
    parent = qwidget.parent()
    while (parent := qwidget.parent()) is not None:
        qwidget = parent
    
    return getattr(qwidget, "_table_viewer", None)

def get_tables(widget: Widget | QWidget):
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return v.tables

def get_table_data(widget: Widget | QWidget):
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return [(table.name, table.data) for table in v.tables]

def open_viewer(gui, result: TableViewer, return_type: type):
    result.show()
    
def add_table_to_viewer(gui, result: Any, return_type: type):
    viewer = find_table_viewer_ancestor(gui)
    if viewer is None:
        return
    viewer.add_layer(result)
    
def add_table_data_to_viewer(gui, result: Any, return_type: type):
    viewer = find_table_viewer_ancestor(gui)
    if viewer is None:
        return
    viewer.add_table(result)

register_type(TableViewer, return_callback=open_viewer, choices=find_table_viewer_ancestor)
register_type(TableLayer, return_callback=add_table_to_viewer, choices=get_tables)
register_type(TableData, return_callback=add_table_data_to_viewer, choices=get_table_data)

# Widget
class ColumnChoice(Container):
    def __init__(
        self,
        data_choices: Iterable[pd.DataFrame] | Callable[[Widget], Iterable[pd.DataFrame]],
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

register_type(TableColumn, widget_type=ColumnChoice, data_choices=get_table_data)
