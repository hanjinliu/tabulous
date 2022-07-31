from ._mainwidgets import QMainWindow, QMainWidget, _QtMainWidgetBase

# activate key combo
from . import _keycombo

del _keycombo

__all__ = ["QMainWindow", "QMainWidget", "_QtMainWidgetBase"]
