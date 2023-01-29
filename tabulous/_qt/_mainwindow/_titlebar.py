from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt, Signal
from tabulous._qt._svg import QColoredSVGIcon

if TYPE_CHECKING:
    from tabulous._qt._mainwindow._base import _QtMainWidgetBase

ICON_DIR = Path(__file__).parent.parent / "_icons"


class QMainWindowTitleBar(QtW.QMenuBar):
    def __init__(self, parent: QtW.QMainWindow, icon: QtGui.QIcon) -> None:
        super().__init__(parent)
        self.setFixedHeight(28)
        self._title_icon = self.addMenu(icon, "icon")
        self._title_icon.setEnabled(False)
        self._drag_start = None

        self._corner_buttons = QCornerButtons(self)
        self.setCornerWidget(self._corner_buttons)
        self._corner_buttons.minimizeSignal.connect(self._minimize_window)
        self._corner_buttons.middleSignal.connect(self._toggle_maximize_window)
        self._corner_buttons.closeSignal.connect(self._close_window)

    def setIconColor(self, color: QtGui.QColor):
        self._corner_buttons.setIconColors(color, self.parentWidget().windowState())

    def _minimize_window(self):
        return self.parentWidget().setWindowState(Qt.WindowState.WindowMinimized)

    def _toggle_maximize_window(self):
        parent = self.parentWidget()
        parent.toggleWindowState()
        self._corner_buttons.setMiddleIcon(parent.windowState())

    def _close_window(self):
        return self.parentWidget().close()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag_start = event.pos()
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._drag_start = None
        return super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent) -> None:
        self._toggle_maximize_window()
        return super().mouseDoubleClickEvent(a0)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._drag_start is not None:
            self.parentWidget().move(self.mapToGlobal(event.pos() - self._drag_start))

        return super().mouseMoveEvent(event)

    if TYPE_CHECKING:

        def parentWidget(self) -> _QtMainWidgetBase:
            ...


class QCornerButtons(QtW.QToolBar):
    minimizeSignal = Signal()
    middleSignal = Signal()
    closeSignal = Signal()

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setMaximumHeight(21)
        self._minimize_icon = QColoredSVGIcon.fromfile(ICON_DIR / "minimize.svg")
        self._maximize_inv_icon = QColoredSVGIcon.fromfile(
            ICON_DIR / "maximize_invert.svg"
        )
        self._maximize_icon = QColoredSVGIcon.fromfile(ICON_DIR / "maximize.svg")
        self._close_icon = QColoredSVGIcon.fromfile(ICON_DIR / "close.svg")

        self._minimize_action = self.addAction(
            "minimize window", self.minimizeSignal.emit
        )
        self._minimize_action.setIcon(self._minimize_icon)
        self._middle_action = self.addAction(
            "toggle window size", self.middleSignal.emit
        )
        self._middle_action.setIcon(self._maximize_icon)
        self._close_action = self.addAction("close window", self.closeSignal.emit)
        self._close_action.setIcon(self._close_icon)

        # hover effect
        close_button = self.widgetForAction(self._close_action)
        close_button.setObjectName("cornerCloseButton")
        close_button.setStyleSheet(
            "#cornerCloseButton:hover { background-color: #FF1818; }"
        )

    def setMiddleIcon(self, state: Qt.WindowState):
        if state == Qt.WindowState.WindowMaximized:
            self._middle_action.setIcon(self._maximize_inv_icon)
        else:
            self._middle_action.setIcon(self._maximize_icon)

    def setIconColors(self, color: QtGui.QColor, state: Qt.WindowState):
        self._minimize_icon = self._minimize_icon.colored(color)
        self._maximize_icon = self._maximize_icon.colored(color)
        self._maximize_inv_icon = self._maximize_inv_icon.colored(color)
        self._close_icon = self._close_icon.colored(color)

        self._minimize_action.setIcon(self._minimize_icon)
        if state == Qt.WindowState.WindowMaximized:
            self._middle_action.setIcon(self._maximize_inv_icon)
        else:
            self._middle_action.setIcon(self._maximize_icon)
        self._close_action.setIcon(self._close_icon)
