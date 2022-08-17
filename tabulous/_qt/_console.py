from __future__ import annotations
from qtconsole.rich_jupyter_widget import RichJupyterWidget
import weakref
from typing import TYPE_CHECKING, cast
from qtpy.QtCore import Signal, Qt
from qtpy import QtWidgets as QtW, QtCore, QtGui

if TYPE_CHECKING:
    from ..widgets.mainwindow import TableViewerBase

    class RichJupyterWidget(RichJupyterWidget, QtW.QWidget):
        ...


# Modified from napari_console https://github.com/napari/napari-console
class QtConsole(RichJupyterWidget):
    codeExecuted = Signal(str)

    def __init__(self, *args, **kwargs):
        self._old_point = None
        super().__init__(*args, **kwargs)
        self.setMinimumSize(100, 0)
        self.resize(100, 40)
        self._dock_parent = None

    def connect_parent(self, widget: TableViewerBase):
        from IPython import get_ipython
        from IPython.terminal.interactiveshell import TerminalInteractiveShell
        from ipykernel.connect import get_connection_file
        from ipykernel.inprocess.ipkernel import InProcessInteractiveShell
        from ipykernel.zmqshell import ZMQInteractiveShell
        from qtconsole.client import QtKernelClient
        from qtconsole.inprocess import QtInProcessKernelManager

        shell = get_ipython()

        if shell is None:
            # If there is no currently running instance create an in-process
            # kernel.
            kernel_manager = QtInProcessKernelManager()
            kernel_manager.start_kernel(show_banner=False)
            kernel_manager.kernel.gui = "qt"

            kernel_client = kernel_manager.client()
            kernel_client.start_channels()

            self.kernel_manager = kernel_manager
            self.kernel_client = kernel_client
            self.shell = kernel_manager.kernel.shell
            self.push = self.shell.push

        elif type(shell) == InProcessInteractiveShell:
            # If there is an existing running InProcessInteractiveShell
            # it is likely because multiple viewers have been launched from
            # the same process. In that case create a new kernel.
            # Connect existing kernel
            kernel_manager = QtInProcessKernelManager(kernel=shell.kernel)
            kernel_client = kernel_manager.client()

            self.kernel_manager = kernel_manager
            self.kernel_client = kernel_client
            self.shell = kernel_manager.kernel.shell
            self.push = self.shell.push

        elif isinstance(shell, TerminalInteractiveShell):
            # if launching from an ipython terminal then adding a console is
            # not supported. Instead users should use the ipython terminal for
            # the same functionality.
            self.kernel_client = None
            self.kernel_manager = None
            self.shell = None
            self.push = lambda var: None

        elif isinstance(shell, ZMQInteractiveShell):
            # if launching from jupyter notebook, connect to the existing
            # kernel
            kernel_client = QtKernelClient(connection_file=get_connection_file())
            kernel_client.load_connection_file()
            kernel_client.start_channels()

            self.kernel_manager = None
            self.kernel_client = kernel_client
            self.shell = shell
            self.push = self.shell.push
        else:
            raise ValueError("ipython shell not recognized; " f"got {type(shell)}")

        if self.shell is not None:
            from .._global_variables import default_namespace as _ns
            import tabulous as tbl
            import numpy as np
            import pandas as pd

            ns = {
                _ns.viewer: widget,
                _ns.numpy: np,
                _ns.pandas: pd,
                _ns.tabulous: tbl,
            }
            self.shell.push(ns)

    def setFocus(self):
        """Set focus to the text edit."""
        return self._control.setFocus()

    def buffer(self) -> str:
        """Get current code block"""
        return self.input_buffer

    def setBuffer(self, code: str) -> None:
        """Set code string to Jupyter QtConsole buffer"""
        self.input_buffer = ""
        if not isinstance(code, str):
            raise ValueError(f"Cannot set {type(code)}.")
        cursor = self._control.textCursor()
        lines = code.split("\n")
        for line in lines[:-1]:
            cursor.insertText(line + "\n")
            self._insert_continuation_prompt(cursor)  # insert "...:"
        cursor.insertText(lines[-1])
        return None

    def execute(
        self,
        source: str | None = None,
        hidden: bool = False,
        interactive: bool = False,
    ):
        """Execute current code block."""
        if source is None:
            source = self.input_buffer
        super().execute(source=source, hidden=hidden, interactive=interactive)
        self.codeExecuted.emit(source)
        return None

    # NOTE: qtconsole overwrites "parent" method so we have to use another method to manage parent.
    def dockParent(self):
        """Return the dock widget parent."""
        if self._dock_parent is None:
            return None
        return self._dock_parent()

    def setDockParent(self, widget: QtW.QDockWidget):
        """Set the dock widget parent."""
        if not isinstance(widget, QtW.QDockWidget):
            raise TypeError("Parent must be a QDockWidget")
        self._dock_parent = weakref.ref(widget)

    def eventFilter(self, obj, event: QtCore.QEvent):
        """Reimplemented to ensure a console-like behavior in the underlying
        text widgets.
        """
        etype = event.type()
        if etype == QtCore.QEvent.Type.KeyPress:
            parent = self.dockParent()
            if parent is None:
                return super().eventFilter(obj, event)

            event = cast(QtGui.QKeyEvent, event)
            key = event.key()
            mod = event.modifiers()

            # float/unfloat dock widget
            if (
                mod & Qt.KeyboardModifier.ControlModifier
                and mod & Qt.KeyboardModifier.ShiftModifier
                and key in (Qt.Key.Key_Up, Qt.Key.Key_Down)
            ):
                self.setDockFloating(key == Qt.Key.Key_Up)
                return True
            elif (
                mod & Qt.KeyboardModifier.ControlModifier
                and mod & Qt.KeyboardModifier.ShiftModifier
                and key == Qt.Key.Key_C
            ):
                if not parent.isFloating():
                    return super().eventFilter(obj, event)
                parent.parentWidget().toggleConsoleVisibility()

        return super().eventFilter(obj, event)

    def setDockFloating(self, floating: bool):
        parent = self.dockParent()
        if parent is None:
            return
        if floating:
            parent.setFloating(True)
            QtCore.QTimer.singleShot(0, parent.activateWindow)
        else:
            parent.setFloating(False)
            self._control.ensureCursorVisible()
            self._control.setTextCursor(self._control.textCursor())

        if floating:
            if self._old_point is None:
                _screen_rect = QtW.QApplication.desktop().screen().rect()
                _screen_center = _screen_rect.center()
                parent.resize(500, 600)
                pos = _screen_center - self.rect().center()
            else:
                pos = self._old_point
            parent.move(pos)
            self._old_point = pos
        parent.setFocus()
        self.setFocus()
        return None
