__version__ = "0.0.1.dev0"

from .widgets import TableLayer, TableViewer
from .core import read_csv, read_excel

__all__ = [
    "TableLayer",
    "TableViewer",
    "read_csv",
    "read_excel",
]

from . import _magicgui

# TODO: merge tab list and tab stack.
# This is because at least QListWidget+QStackedWidget and QTabWidget have different
# layouts. 

# Mainwindow ---+--> QTableListWidget ---+--> QTableStackWidget
#               |                        |
#               +--> ...???              +--> QTabs