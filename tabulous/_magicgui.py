from __future__ import annotations
from typing import NewType
from qtpy.QtWidgets import QWidget
from magicgui import register_type
from magicgui.widgets import Widget
import pandas as pd

from .widgets import TableViewer, TableLayer

def find_table_viewer_ancestor(widget: Widget | QWidget) -> TableViewer | None:
    if isinstance(widget, Widget):
        qwidget = widget.native
    elif isinstance(widget, QWidget):
        qwidget = widget
    else:
        raise TypeError(f"Cannot use {type(widget)} as an input.")
    qwidget: QWidget
    parent = qwidget.parent()
    while parent is not None:
        parent = parent.parent()
    return getattr(parent, "_mainwindow", None)

def get_tables(widget: Widget | QWidget):
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return v.tables

def get_table_data(widget: Widget | QWidget):
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return [table.data for table in v.tables]

TableData = NewType("TableData", pd.DataFrame)

register_type(TableViewer, choices=find_table_viewer_ancestor)
register_type(TableLayer, choices=get_tables)
register_type(TableData, choices=get_table_data)
