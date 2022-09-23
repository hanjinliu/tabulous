__version__ = "0.2.1"

from .widgets import Table, TableViewer, TableViewerWidget
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
    "Table",
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
