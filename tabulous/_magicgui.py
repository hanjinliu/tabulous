from __future__ import annotations
from typing import Any
from qtpy.QtWidgets import QWidget
from magicgui import register_type
from magicgui.widgets import Widget

from .widgets import TableViewer, TableLayer
from .types import TableData

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
    return [table.data for table in v.tables]

def open_viewer(gui, result: Any, return_type: type):
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
