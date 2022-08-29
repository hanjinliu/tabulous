from __future__ import annotations
from typing import Any, Callable, Generic, TypeVar
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtWidgets import QAction

_T = TypeVar("_T")


class QActionRegistry(QtCore.QObject, Generic[_T]):
    def __init__(self, *args, **kwargs) -> None:
        self._qt_context_menu = QContextMenu(self)

    def registerAction(self, location: str):
        locs = location.split(">")
        menu = self._qt_context_menu
        for loc in locs[:-1]:
            a = menu.searchChild(loc)
            if a is None:
                menu = menu.addMenu(loc)
            elif not isinstance(a, QContextMenu):
                i = locs.index(loc)
                err_loc = ">".join(locs[:i])
                raise TypeError(f"{err_loc} is not a menu.")
            else:
                menu = a

        def wrapper(f: Callable[[_T], Any]):
            action = QAction(locs[-1], self)
            action.triggered.connect(lambda: f(self._qt_context_menu._current_index))
            menu.addAction(action)
            return f

        return wrapper

    def execContextMenu(self, index: _T) -> None:
        return self._qt_context_menu.execAtIndex(QtGui.QCursor().pos(), index)


class QContextMenu(QtW.QMenu):
    """Contextmenu for the tabs on the QTabWidget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_index = None
        self._actions: dict[str, QAction | QContextMenu] = {}

    def addMenu(self, title: str) -> QContextMenu:
        """Add a submenu to the contextmenu."""
        menu = self.__class__(self)
        action = super().addMenu(menu)
        action.setText(title)
        self._actions[title] = menu
        return menu

    def addAction(self, action: QAction) -> None:
        super().addAction(action)
        self._actions[action.text()] = action
        return None

    def execAtIndex(self, pos: QtCore.QPoint, index: _T):
        """Execute contextmenu at index."""
        self._current_index = index
        try:
            self.exec_(pos)
        finally:
            self._current_index = None
        return None

    def searchChild(self, name: str) -> QAction | QContextMenu | None:
        """Return a action that matches the name."""
        return self._actions.get(name, None)
