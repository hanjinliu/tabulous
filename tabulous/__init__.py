__version__ = "0.3.0.dev0"

from .widgets import TableViewer, TableViewerWidget
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
