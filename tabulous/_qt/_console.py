from __future__ import annotations

from pathlib import Path
import weakref
from typing import TYPE_CHECKING, cast
from contextlib import suppress

from qtpy.QtCore import Signal
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtconsole.rich_jupyter_widget import RichJupyterWidget

from tabulous._keymap import QtKeys, QtKeyMap

if TYPE_CHECKING:
    from tabulous._qt._dockwidget import QtDockWidget
    from tabulous.widgets._mainwindow import TableViewerBase

    class RichJupyterWidget(RichJupyterWidget, QtW.QWidget):
        """To fix typing problem"""


# Modified from napari_console https://github.com/napari/napari-console
class QtConsole(RichJupyterWidget):
    codeExecuted = Signal(str)
    _keymap = QtKeyMap()

    def __init__(self, *args, **kwargs):
        self._old_point = None
        super().__init__(*args, **kwargs)
        self.setMinimumSize(100, 0)
        self.resize(100, 40)
        self._dock_parent = None
        self.codeExecuted.connect(self.setFocus)

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
            self.shell: InProcessInteractiveShell = kernel_manager.kernel.shell
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
            raise ValueError(f"ipython shell not recognized, got {type(shell)}")

        if self.shell is not None:

            from IPython.paths import get_ipython_dir
            from tabulous._utils import get_config

            config = get_config()
            _ns = config.console_namespace

            # run IPython startup files
            profile_dir = Path(get_ipython_dir()) / "profile_default" / "startup"
            if profile_dir.exists() and _ns.load_startup_file:
                import runpy

                _globals = {}
                for startup in profile_dir.glob("*.py"):
                    with suppress(Exception):
                        _globals.update(runpy.run_path(startup))

                self.shell.push(_globals)

            # update namespaces
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
        self._control.setFocus()
        cursor = self._control.textCursor()
        cursor.clearSelection()
        self._control.setTextCursor(cursor)
        return None

    def isActive(self) -> bool:
        return self.isVisible() and self.shell is not None

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

    def insertText(self, text: str) -> None:
        cursor = self._control.textCursor()
        cursor.insertText(text)
        return None

    def setTempText(self, text: str | None = None) -> None:
        if text is None:
            text = "viewer.data.loc[...]"
        cursor = self._control.textCursor()
        cursor.removeSelectedText()
        pos = cursor.position()
        cursor.insertText(text)
        cursor.setPosition(pos)
        cursor.setPosition(pos + len(text), QtGui.QTextCursor.MoveMode.KeepAnchor)
        self._control.setTextCursor(cursor)
        return None

    def selectedText(self) -> str:
        """Return the selected text"""
        cursor = self._control.textCursor()
        return cursor.selection().toPlainText()

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

    # NOTE: qtconsole overwrites "parent" method so we have to use another method to
    # manage parent.
    def dockParent(self) -> QtDockWidget:
        """Return the dock widget parent."""
        if self._dock_parent is None:
            return None
        return self._dock_parent()

    def setDockParent(self, widget: QtDockWidget):
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
            keys = QtKeys(event)
            if self._keymap.press_key(keys):
                return True

        return super().eventFilter(obj, event)

    def update_console(self, ns: dict) -> None:
        """Update the console namespace."""
        self.shell.push(dict(ns))
        return None

    @_keymap.bind("Ctrl+Shift+Down", floating=False)
    @_keymap.bind("Ctrl+Shift+Up", floating=True)
    def setDockFloating(self, floating: bool):
        """Make the parent dock widget floating."""
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
                _screen_rect = QtGui.QGuiApplication.primaryScreen().geometry()
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

    @_keymap.bind("Ctrl+Shift+C", keys="Ctrl+Shift+C")
    @_keymap.bind("Ctrl+Shift+F", keys="Ctrl+Shift+F")
    def _press_parent_keycombo(self, keys: str):
        parent = self.dockParent()
        if parent is None:
            return
        parent.parentWidget()._keymap.press_key(keys)

    @_keymap.bind("Ctrl+.")
    def _ignore(self):
        """Ignore restarting the kernel."""
        parent = self.parentWidget()
        while parent is not None:
            parent = parent.parentWidget()
            if hasattr(parent, "_table_viewer"):
                parent._keymap.press_key("Ctrl+.")
                break

    def update_theme(self, theme: str):
        from tabulous.style import Style
        from tabulous.color import normalize_color

        style = Style.from_global(theme)
        stylesheet = style.format_file()
        self.style_sheet = stylesheet

        # Set syntax styling and highlighting using theme
        light_theme = sum(normalize_color(style.background)[:3]) > 382.5
        if light_theme:
            self.syntax_style = "default"
        else:
            self.syntax_style = "vim"
        bracket_color = QtGui.QColor(*normalize_color(style.highlight0))
        self._bracket_matcher.format.setBackground(bracket_color)
