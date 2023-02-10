from __future__ import annotations
from typing import TYPE_CHECKING, Any, cast
import qtpy
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import QEvent, Signal, Qt
from qt_command_palette import get_palette

from ._namespace import Namespace

from tabulous._qt._table import QSpreadSheet
from tabulous._qt._table_stack import QTabbedTableStack
from tabulous._qt._history import QtFileHistoryManager
from tabulous._keymap import QtKeyMap
from tabulous.types import TabPosition
from tabulous._utils import load_cell_namespace
from tabulous.style import Style

if TYPE_CHECKING:
    from tabulous._qt._toolbar import QTableStackToolBar
    from tabulous._qt._mainwindow._titlebar import QMainWindowTitleBar
    from tabulous._qt._console import QtConsole
    from tabulous.widgets import TableViewer


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
    _menubar: QMainWindowTitleBar
    _keymap: QtKeyMap
    _namespace: Namespace

    _hist_mgr = QtFileHistoryManager()
    _is_mainwindow = False

    def __init__(
        self,
        tab_position: TabPosition | str = TabPosition.top,
    ):
        super().__init__()
        self.setObjectName(f"tabulous.{type(self).__name__}")
        tab_position = TabPosition(tab_position)
        self._tablestack = QTabbedTableStack(tab_position=tab_position.name)
        self._toolbar = None
        self._menubar = None
        self._style_theme = "none"
        self.setCentralWidget(self._tablestack)

        # NOTE: Event filter must be stored as an attribute, otherwise it will be
        # garbage collected.
        self._event_filter = _EventFilter()
        self.installEventFilter(self._event_filter)
        self._white_background = True
        self._event_filter.styleChanged.connect(self.updateWidgetStyle)
        self._console_widget: QtConsole | None = None
        self._keymap_widget = None

        # Queued namespaces for console
        self._queued_ns: dict[str, Any] = {}

        # update with user namespace
        self._namespace = Namespace()
        self._namespace.update_safely(load_cell_namespace())

        # install command palette
        self._command_palette = get_palette("tabulous")
        self._command_palette.install(self)
        qcommand_palette = self._command_palette.get_widget(self)
        qcommand_palette.hidden.connect(self._on_hidden)
        qcommand_palette.setFont(QtGui.QFont("Arial", 10))

    def _on_hidden(self):
        try:
            self.setCellFocus()
        except AttributeError:
            pass

    def showCommandPalette(self):
        self._command_palette.show_widget(self)
        return None

    def backgroundColor(self):
        return self.palette().color(self.backgroundRole())

    def applyTheme(self, theme: str):
        """Apply predefined theme to the main window."""
        if self._style_theme == theme:
            return
        self._style_theme = theme
        self.setStyleSheet(Style.from_global(self._style_theme).format_file())
        # update console theme
        if console := self._console_widget:
            console.update_theme(theme)

    def showPreferenceDialog(self):
        from tabulous._qt._preference import QPreferenceDialog

        dlg = QPreferenceDialog(self)
        dlg.exec()

    def updateWidgetStyle(self):
        bg = self.backgroundColor()
        if self._style_theme.startswith("dark"):
            _white = False
        elif self._style_theme.startswith("light"):
            _white = True
        else:
            _white = bg.red() + bg.green() + bg.blue() > 128 * 3
        self._white_background = _white
        if _white:
            color = "#1E1E1E"
        else:
            color = "#CCCCCC"
        # update toolbar tool button colors
        if self._toolbar is not None:
            self._toolbar.setToolButtonColor(color)

        # custom title bar
        if self._menubar is not None:
            self._menubar.setIconColor(color)

        # update header button colors
        if self._tablestack.isEmpty():
            return
        for i in range(self._tablestack.count()):
            table = self._tablestack.tableAtIndex(i)
            if isinstance(table, QSpreadSheet):
                table = cast(QSpreadSheet, table)
                table.model()._out_of_bound_color_cache = None
            for wdt in table._header_widgets().values():
                if hasattr(wdt, "updateColor"):
                    wdt.updateColor(color)

    def screenshot(self):
        """Create an array of pixel data of the current view."""
        import numpy as np

        img = self.grab().toImage()
        bits = img.constBits()
        h, w, c = img.height(), img.width(), 4
        if qtpy.API_NAME.startswith("PySide"):
            arr = np.array(bits).reshape(h, w, c)
        else:
            bits.setsize(h * w * c)
            arr: np.ndarray = np.frombuffer(bits, np.uint8)
            arr = arr.reshape(h, w, c)

        return arr[:, :, [2, 1, 0, 3]]

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        """Activate keymap object."""
        if self._keymap.press_key(a0):
            return None
        return super().keyPressEvent(a0)

    def showKeyMap(self) -> None:
        """Show keymap viewer widget."""
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
        if table is None or table.table_shape[0] * table.table_shape[1] == 0:
            return None
        sels = table.selections
        if len(sels) == 0:
            table.selections = [(slice(0, 1), slice(0, 1))]

        # set focus
        idx = self._tablestack.currentIndex()
        if len(self._tablestack.tiledIndices(idx)) > 1:
            idx_group = self._tablestack._tab_index_to_group_index(idx)
            self._tablestack.widget(idx).setFocusedIndex(idx_group)
        else:
            table._qwidget._qtable_view.setFocus()
        return None

    def setCentralWidget(self, wdt: QTabbedTableStack):
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

    def statusBar(self) -> QtW.QStatusBar:
        raise NotImplementedError()

    def toggleWindowState(self):
        if self.windowState() == Qt.WindowState.WindowMaximized:
            self.setWindowState(Qt.WindowState.WindowNoState)
        else:
            self.setWindowState(Qt.WindowState.WindowMaximized)
        if self._menubar is not None:
            self._menubar._corner_buttons.setMiddleIcon(self.windowState())

    def setTableSelection(self, sl: tuple[slice, slice]):
        """Set selection slices to the table selection editor"""
        if table := self._table_viewer.current_table:
            sel = list(table.selections)
            self._toolbar.blockSignals(True)
            sel[-1] = sl
            table.selections = sel
            self._toolbar.blockSignals(False)
