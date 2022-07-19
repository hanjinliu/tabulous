__version__ = "0.1.0a1"

from .widgets import TableView, TableViewer, TableViewerWidget
from .core import (
    current_viewer,
    read_csv,
    read_excel,
    view_table,
    view_spreadsheet,
    open_sample,
)
from ._magicgui import MagicTableViewer

__all__ = [
    "TableView",
    "TableViewer",
    "TableViewerWidget",
    "MagicTableViewer",
    "current_viewer",
    "read_csv",
    "read_excel",
    "view_table",
    "view_spreadsheet",
    "open_sample",
]
