from __future__ import annotations

from qtpy import QtWidgets as QtW

from tabulous._qt._mainwindow import QMainWindow
from tabulous._utils import get_config, update_config
from tabulous._magicgui._toggle_switch import QToggleSwitch


class QGeneralPanel(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def get_updated_config(self):
        cfg = get_config()
        cfg.window.ask_on_close = self._ask_on_close.isChecked()
        cfg.window.notify_latest = self._notify_latest.isChecked()
        cfg.window.selection_editor = self._selection_editor.isChecked()
        cfg.window.show_console = self._show_console.isChecked()
        return cfg

    def _update_config(self):
        cfg = self.get_updated_config()
        update_config(cfg)
        QMainWindow.reload_config()

    def _setup_ui(self):
        from tabulous._utils import get_config

        cfg = get_config()

        self._ask_on_close = QToggleSwitch()
        self._ask_on_close.setChecked(cfg.window.ask_on_close)

        self._notify_latest = QToggleSwitch()
        self._notify_latest.setChecked(cfg.window.notify_latest)

        self._selection_editor = QToggleSwitch()
        self._selection_editor.setChecked(cfg.window.selection_editor)

        self._show_console = QToggleSwitch()
        self._show_console.setChecked(cfg.window.show_console)

        _layout = QtW.QFormLayout()

        _layout.addRow("Ask before closing window", self._ask_on_close)
        _layout.addRow("Notify latest version", self._notify_latest)
        _layout.addRow("Show selection editor", self._selection_editor)
        _layout.addRow("Show Qt console", self._show_console)

        self._ask_on_close.toggled.connect(self._update_config)
        self._notify_latest.toggled.connect(self._update_config)
        self._selection_editor.toggled.connect(self._update_config)
        self._show_console.toggled.connect(self._update_config)

        self.setLayout(_layout)
