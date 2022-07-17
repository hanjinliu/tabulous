__version__ = "0.0.1.dev0"

from .widgets import TableLayer, TableViewer, TableViewerWidget
from .core import current_viewer, read_csv, read_excel, view_table, view_spreadsheet
from ._magicgui import MagicTableViewer

__all__ = [
    "TableLayer",
    "TableViewer",
    "TableViewerWidget",
    "MagicTableViewer",
    "current_viewer",
    "read_csv",
    "read_excel",
    "view_table",
    "view_spreadsheet",
]

