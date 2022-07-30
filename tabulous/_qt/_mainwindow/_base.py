from __future__ import annotations
from typing import TYPE_CHECKING
import qtpy
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import QEvent, Signal

from .._table_stack import QTabbedTableStack
from .._keymap import QtKeyMap
from ...types import TabPosition

if TYPE_CHECKING:
    from .._toolbar import QTableStackToolBar
    from .._console import _QtConsole
    from ...widgets import TableViewer


class _EventFilter(QtCore.QObject):
    styleChanged = Signal()

    def eventFilter(self, obj: QtCore.QObject, event: QEvent):
        _type = event.type()
        if _type == QEvent.Type.StyleChange:
            self.styleChanged.emit()
        return False


class _QtMainWidgetBase(QtW.QWidget):
    _table_viewer: TableViewer
    _tablestack: QTabbedTableStack
    _toolbar: QTableStackToolBar
    _keymap: QtKeyMap

    def __init__(
        self,
        tab_position: TabPosition | str = TabPosition.top,
    ):
        super().__init__()
        self.setObjectName(f"tabulous.{type(self).__name__}")
        tab_position = TabPosition(tab_position)
        self._tablestack = QTabbedTableStack(tab_position=tab_position.name)
        self.setCentralWidget(self._tablestack)

        # NOTE: Event filter must be stored as an attribute, otherwise it will be
        # garbage collected.
        self._event_filter = _EventFilter()
        self.installEventFilter(self._event_filter)
        self._event_filter.styleChanged.connect(self.updateToolButtons)
        self._console_widget: _QtConsole | None = None
        self._keymap_widget = None

    def updateToolButtons(self):
        if self._toolbar is None:
            return
        bg = self.palette().color(self.backgroundRole())
        whiteness = bg.red() + bg.green() + bg.blue()
        if whiteness < 128 * 3:
            self._toolbar.setToolButtonColor("#FFFFFF")
        else:
            self._toolbar.setToolButtonColor("#000000")

    def screenshot(self):
        import numpy as np

        img = self.grab().toImage()
        bits = img.constBits()
        h, w, c = img.height(), img.width(), 4
        if qtpy.API_NAME.startswith("PySide"):
            arr = np.array(bits).reshape(h, w, c)
        else:
            bits.setsize(h * w * c)
            arr = np.frombuffer(bits, np.uint8).reshape(h, w, c)

        return arr[:, :, [2, 1, 0, 3]]

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if not self._keymap.press_key(a0):
            return super().keyPressEvent(a0)
        return None

    def showKeyMap(self) -> None:
        if self._keymap_widget is None:
            wdt = self._keymap.to_widget()
            wdt.setParent(self, wdt.windowFlags())
            self._keymap_widget = wdt
        self._keymap_widget.show()
        self._keymap_widget.showNormal()
        return None

    def setCellFocus(self) -> None:
        """Set focus to the current table."""
        table = self._table_viewer.current_table
        if table is None or table.data is None:
            return None
        sels = table.selections
        table._qwidget._qtable_view.setFocus()
        if len(sels) == 0:
            sels = [(slice(0, 1), slice(0, 1))]
        table.selections = [sels[0]]
        return None

    def setCentralWidget(self, wdt: QtW.QWidget):
        """Set the splitter widget."""
        raise NotImplementedError()

    def toolBarVisible(self) -> bool:
        """Visibility of toolbar"""
        raise NotImplementedError()

    def setToolBarVisible(self, visible: bool):
        """Set visibility of toolbar"""
        raise NotImplementedError()

    def toggleToolBarVisibility(self):
        """Toggle visibility of toolbar"""
        return self.setToolBarVisible(not self.toolBarVisible())

    def addDefaultToolBar(self):
        """Add default toolbar widget regardless of self is a main window or not."""
        raise NotImplementedError()

    def consoleVisible(self) -> bool:
        """True if embeded console is visible."""
        raise NotImplementedError()

    def setConsoleVisible(self, visible: bool) -> None:
        """Set visibility of embeded console widget."""
        raise NotImplementedError()

    def toggleConsoleVisibility(self) -> None:
        """Toggle visibility of embeded console widget."""
        return self.setConsoleVisible(not self.consoleVisible())
