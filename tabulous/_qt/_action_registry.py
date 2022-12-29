from __future__ import annotations
from typing import Any, Callable, Generic, TypeVar
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtWidgets import QAction

_T = TypeVar("_T")


class QActionRegistry(QtCore.QObject, Generic[_T]):
    """
    An contextmenu action registry.

    This class must be subclassed with other QWidget class like below.

    >>> class MyWidget(QWidget, QActionRegistry[int]):
    >>>     def __init__(self, parent=None):
    >>>         QWidget.__init__(self, parent)
    >>>         QActionRegistry.__init__(self)

    Now you can register any Python function with signature f(i: _T) to the context
    menu.
    """

    def __init__(self, *args, **kwargs) -> None:
        self._qt_context_menu = QContextMenu(self)

    def registerAction(self, location: str):
        """Register a function to the context menu at the given location."""
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

    def addSeparator(self, location: str | None = None):
        """Add separator at the given location."""
        menu = self._qt_context_menu
        if location is None:
            locs = []
        else:
            locs = location.split(">")

        for loc in locs:
            a = menu.searchChild(loc)
            if a is None:
                raise ValueError(f"{location} is not a valid location.")
            elif not isinstance(a, QContextMenu):
                i = locs.index(loc)
                err_loc = ">".join(locs[:i])
                raise TypeError(f"{err_loc} is not a menu.")
            else:
                menu = a

        menu.addSeparator()
        return None

    def execContextMenu(self, pos: QtCore.QPoint, index: _T) -> None:
        """Execute the context menu at the given index."""
        return self._qt_context_menu.execAtIndex(pos, index)


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
        if not self._actions:
            # don't show contextmenu if no action is registered.
            return None
        self._current_index = index
        try:
            self.exec_(pos)
        finally:
            self._current_index = None
        return None

    def searchChild(self, name: str) -> QAction | QContextMenu | None:
        """Return a action that matches the name."""
        return self._actions.get(name, None)
