from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path
import weakref
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt, QEvent, QTimer

from ._base import _QtMainWidgetBase
from tabulous._keymap import QtKeyMap
from tabulous.types import TabPosition
from tabulous._utils import get_config

if TYPE_CHECKING:
    from tabulous.widgets import TableViewer
    from tabulous._qt._table_stack import QTabbedTableStack
    from tabulous._qt._dockwidget import QtDockWidget

ICON_DIR = Path(__file__).parent.parent / "_icons"
STYLE_DIR = Path(__file__).parent.parent


class QMainWidget(QtW.QSplitter, _QtMainWidgetBase):
    _keymap = QtKeyMap()

    def __init__(self, tab_position: TabPosition | str = TabPosition.top):
        QtW.QSplitter.__init__(self)
        _QtMainWidgetBase.__init__(self, tab_position)
        self.setOrientation(Qt.Orientation.Vertical)
        self._toolbar = None
        self._statusbar = QRichStatusBar(self)
        self._statusbar.setFixedHeight(25)
        self.addWidget(self._statusbar)

    def setCentralWidget(self, wdt: QTabbedTableStack):
        """Mimicking QMainWindow's method by adding a widget to the layout."""
        self.addWidget(wdt)
        wdt.setMinimumSize(200, 200)
        self.setMinimumSize(200, 200)
        return None

    def toolBarVisible(self) -> bool:
        """Visibility of toolbar"""
        if self._toolbar is None:
            return False
        else:
            return self._toolbar.isVisible()

    def setToolBarVisible(self, visible: bool):
        """Set visibility of toolbar"""
        if visible and self._toolbar is None:
            from tabulous._qt._toolbar import QTableStackToolBar

            self._toolbar = QTableStackToolBar(self)
            self.insertWidget(0, self._toolbar)
            self.updateWidgetStyle()

        return self._toolbar.setVisible(visible)

    def consoleVisible(self) -> bool:
        """True if embeded console is visible."""
        if self._console_widget is None:
            return False
        else:
            return self._console_widget.isVisible()

    def setConsoleVisible(self, visible: bool) -> None:
        """Set visibility of embeded console widget."""
        if visible and self._console_widget is None:
            from tabulous._qt._console import QtConsole

            qtconsole = QtConsole()
            qtconsole.connect_parent(self._table_viewer)
            self.addWidget(qtconsole)
            self._console_widget = qtconsole

            if qtconsole.shell is not None:
                qtconsole.update_console(self._queued_ns)
                self._queued_ns.clear()

        self._console_widget.setVisible(visible)

        if visible:
            self._console_widget.setFocus()
        else:
            self.setCellFocus()

    def statusBar(self) -> QRichStatusBar:
        return self._statusbar


_REORDER_INSTANCES = frozenset({QEvent.Type.WindowActivate, QEvent.Type.ZOrderChange})

_HIDE_TOOLTIPS = frozenset(
    {
        QEvent.Type.MouseButtonPress,
        QEvent.Type.MouseButtonDblClick,
        QEvent.Type.KeyPress,
        QEvent.Type.Move,
        QEvent.Type.Resize,
        QEvent.Type.Show,
        QEvent.Type.Hide,
        QEvent.Type.Close,
        QEvent.Type.WindowStateChange,
        QEvent.Type.WindowDeactivate,
        QEvent.Type.FocusOut,
        QEvent.Type.ZOrderChange,
    }
)


class QMainWindow(QtW.QMainWindow, _QtMainWidgetBase):
    _instances: list[QMainWindow] = []
    _keymap = QtKeyMap()
    _dock_widgets: weakref.WeakValueDictionary[str, QtDockWidget]

    def __init__(
        self,
        tab_position: TabPosition | str = TabPosition.top,
    ):
        super().__init__()
        _QtMainWidgetBase.__init__(self, tab_position=tab_position)
        self.setWindowTitle("tabulous")
        self.setWindowIcon(QtGui.QIcon(str(ICON_DIR / "window_icon.png")))
        with open(STYLE_DIR / "_style.qss") as f:
            style = f.read()
        self.setStyleSheet(style)

        self._console_dock_widget = None
        self._dock_widgets = weakref.WeakValueDictionary()

        from tabulous._utils import get_config
        from tabulous._qt._toolbar import QTableStackToolBar

        _config = get_config()
        self._ask_on_close = _config.window.ask_on_close

        self._toolbar = QTableStackToolBar(self)
        self.addToolBar(self._toolbar)
        self._toolbar.setMovable(False)  # nested toolbar causes layout problems
        self._tablestack.setMinimumSize(400, 250)
        self.resize(800, 600)
        self.setStatusBar(QRichStatusBar(self))
        QMainWindow._instances.append(self)

        if _config.window.show_console:
            self.setConsoleVisible(True)

    def consoleVisible(self) -> bool:
        """True if embeded console is visible."""
        if self._console_widget is None:
            return False
        else:
            return self._console_widget.isVisible()

    def setConsoleVisible(self, visible: bool) -> None:
        """Set visibility of embeded console widget."""
        if visible and self._console_widget is None:
            from tabulous._qt._console import QtConsole

            qtconsole = QtConsole()
            qtconsole.connect_parent(self._table_viewer)
            dock = self.addDockWidget(qtconsole, name="Console", area="bottom")
            qtconsole.setDockParent(dock)
            dock.setSourceObject(qtconsole)
            self._console_widget = qtconsole

            if qtconsole.shell is not None:
                qtconsole.update_console(self._queued_ns)
                self._queued_ns.clear()

        else:
            dock = self._console_widget.dockParent()

        dock.setVisible(visible)

        if visible:
            if dock.isFloating():
                QTimer.singleShot(0, dock.activateWindow)
            self._console_widget.setFocus()
        else:
            self.setCellFocus()

    def addDockWidget(
        self,
        qwidget: QtW.QWidget,
        *,
        name: str = "",
        area: str = "right",
        allowed_areas: list[str] = None,
    ):
        from .._dockwidget import QtDockWidget

        name = name or qwidget.objectName()
        dock = QtDockWidget(
            self,
            qwidget,
            name=name.replace("_", " "),
            area=area,
            allowed_areas=allowed_areas,
        )

        super().addDockWidget(QtDockWidget.areas[area], dock)
        return dock

    @classmethod
    def currentViewer(cls) -> TableViewer:
        """Return the current TableViewer widget."""
        window = cls._instances[-1] if cls._instances else None
        return window._table_viewer if window else None

    def close(self, ask: bool | None = False) -> bool:
        if ask is not None:
            self._ask_on_close = ask
        return super().close()

    def event(self, e: QEvent):
        type = e.type()
        if type == QEvent.Type.Close:
            if self._ask_on_close and not self._tablestack.isEmpty():
                msgbox = QtW.QMessageBox(self)
                msgbox.setWindowTitle("tabulous")
                msgbox.setIcon(QtW.QMessageBox.Icon.Question)
                msgbox.setText("Are you sure to close this window?")
                btn = msgbox.addButton(QtW.QMessageBox.StandardButton.Yes)
                msgbox.addButton(QtW.QMessageBox.StandardButton.No)
                btn.setShortcut(QtGui.QKeySequence("Ctrl+W"))

                cbox = QtW.QCheckBox("Don't ask again")
                msgbox.setCheckBox(cbox)
                btn = msgbox.exec()
                if cbox.isChecked():
                    get_config().window.ask_on_close = False
                if btn == QtW.QMessageBox.StandardButton.No:
                    e.ignore()
                    return True
            # when we close the MainWindow, remove it from the instances list
            try:
                QMainWindow._instances.remove(self)
            except ValueError:
                pass
            get_config().as_toml()  # save config

        elif type in _REORDER_INSTANCES:
            # upon activation or raise_, put window at the end of _instances
            try:
                inst = QMainWindow._instances
                inst.append(inst.pop(inst.index(self)))
            except ValueError:
                pass

        elif type in _HIDE_TOOLTIPS:
            self._toolbar.hideTabTooltips()
            self._toolbar.currentToolBar().hideTabTooltips()

        return super().event(e)

    def toolBarVisible(self) -> bool:
        """Visibility of toolbar"""
        return self._toolbar.isVisible()

    def setToolBarVisible(self, visible: bool):
        """Set visibility of toolbar"""
        return self._toolbar.setVisible(visible)


class QRichStatusBar(QtW.QStatusBar):
    """Custom status bar with rich text support."""

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = QtW.QLabel("")
        self._label.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self._label.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.addWidget(self._label)
        self.setContentsMargins(0, 0, 0, 0)

    def showMessage(self, msg: str, timeout: int = 0) -> None:
        self._label.resize(self.width() - 32, self._label.height())
        return self._label.setText(msg)
