from ._mainwidgets import QMainWindow, QMainWidget, _QtMainWidgetBase

# activate command palette and key combo
from . import _command_palette, _keycombo

del _command_palette, _keycombo

__all__ = ["QMainWindow", "QMainWidget", "_QtMainWidgetBase"]
