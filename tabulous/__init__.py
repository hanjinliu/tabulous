__version__ = "0.0.1.dev0"

from .widgets import TableLayer, TableViewer, TableViewerWidget
from .core import read_csv, read_excel
from ._magicgui import MagicTableViewer

__all__ = [
    "TableLayer",
    "TableViewer",
    "TableViewerWidget",
    "MagicTableViewer",
    "read_csv",
    "read_excel",
]

