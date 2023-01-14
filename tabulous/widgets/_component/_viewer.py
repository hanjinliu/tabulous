from __future__ import annotations
from typing import Callable, Any, TYPE_CHECKING
from ._base import ViewerComponent

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase


class Toolbar(ViewerComponent):
    """The toolbar proxy."""

    @property
    def visible(self) -> bool:
        """Visibility of the toolbar."""
        return self.parent._qwidget.toolBarVisible()

    @visible.setter
    def visible(self, val) -> None:
        return self.parent._qwidget.setToolBarVisible(val)

    @property
    def current_index(self) -> int:
        return self.parent._qwidget._toolbar.currentIndex()

    @current_index.setter
    def current_index(self, val: int) -> None:
        return self.parent._qwidget._toolbar.setCurrentIndex(val)

    def register(self, loc: str, f: Callable):
        raise NotImplementedError()


class Console(ViewerComponent):
    """The QtConsole proxy."""

    @property
    def visible(self) -> bool:
        """Visibility of the console."""
        return self.parent._qwidget.consoleVisible()

    @visible.setter
    def visible(self, val) -> None:
        return self.parent._qwidget.setConsoleVisible(val)

    @property
    def is_active(self) -> bool:
        return self.parent._qwidget._console_widget is not None

    def _get_console_widget(self):
        console = self.parent._qwidget._console_widget
        if console is None:
            raise RuntimeError("Console is not active.")
        return console

    @property
    def buffer(self) -> str:
        """Return the current text buffer of the console."""
        return self._get_console_widget().input_buffer

    @buffer.setter
    def buffer(self, val) -> None:
        return self._get_console_widget().setBuffer(val)

    def execute(self):
        """Execute current buffer."""
        return self._get_console_widget().execute()

    def update(self, ns: dict[str, Any]):
        """Update IPython namespace."""
        console = self.parent._qwidget._console_widget
        if console is None:
            self.parent._qwidget._queued_ns.update(ns)
        else:
            self._get_console_widget().update_console(ns)
        return None


class CommandPalette(ViewerComponent):
    def register(
        self,
        command: Callable[[TableViewerBase], Any] | None = None,
        title: str = "User defined",
        desc: str | None = None,
        key: str | None = None,
    ):
        """Register a command."""
        from tabulous.commands import register_command

        if key is not None:
            self.parent.keymap.register(key, command)
        return register_command(command, title=title, desc=desc)

    @property
    def visible(self) -> bool:
        """Visibility of the command palette."""
        qviewer = self.parent._qwidget
        return qviewer._command_palette.get_widget(qviewer).isVisible()

    @visible.setter
    def visible(self, val) -> None:
        qviewer = self.parent._qwidget
        return qviewer._command_palette.get_widget(qviewer).setVisible(val)
