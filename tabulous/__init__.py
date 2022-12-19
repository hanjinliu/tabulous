__version__ = "0.4.0.dev0"

from tabulous.widgets import TableViewer, TableViewerWidget
from tabulous.core import (
    current_viewer,
    read_csv,
    read_excel,
    view_table,
    view_spreadsheet,
    open_sample,
)
from tabulous._magicgui import MagicTableViewer

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
