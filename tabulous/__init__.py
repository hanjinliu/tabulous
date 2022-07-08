__version__ = "0.0.1.dev0"

from .widgets import TableLayer, TableViewer, TableViewerWidget
from .core import read_csv, read_excel

__all__ = [
    "TableLayer",
    "TableViewer",
    "TableViewerWidget",
    "read_csv",
    "read_excel",
]

from . import _magicgui
