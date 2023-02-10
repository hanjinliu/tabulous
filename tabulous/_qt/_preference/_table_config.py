from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui
from superqt.utils import QSignalThrottler
from tabulous._qt._mainwindow import QMainWindow
from tabulous._utils import get_config, update_config


class QTableConfigPanel(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self._throttler = QSignalThrottler(parent=self)
        self._throttler.setTimeout(1000)
        self._throttler.triggered.connect(self._on_throttled)
        self._setup_ui()

    def get_updated_config(self):
        cfg = get_config()
        cfg.table.max_row_count = self._max_row_count.value()
        cfg.table.max_column_count = self._max_column_count.value()
        cfg.table.font = self._font.currentFont().family()
        cfg.table.font_size = self._font_size.value()
        cfg.table.row_size = self._row_size.value()
        cfg.table.column_size = self._column_size.value()
        return cfg

    def _on_throttled(self):
        cfg = self.get_updated_config()
        update_config(cfg)
        QMainWindow.reload_config()

    def _setup_ui(self):
        from tabulous._utils import get_config

        cfg = get_config()

        self._max_row_count = QtW.QSpinBox()
        self._max_row_count.setRange(10_000, 1_000_000)
        self._max_row_count.setValue(cfg.table.max_row_count)

        self._max_column_count = QtW.QSpinBox()
        self._max_column_count.setRange(1_000, 100_000)
        self._max_row_count.setValue(cfg.table.max_column_count)

        self._font = QtW.QFontComboBox()
        self._font.setCurrentFont(QtGui.QFont(cfg.table.font))

        self._font_size = QtW.QSpinBox()
        self._font_size.setRange(6, 28)
        self._font_size.setValue(cfg.table.font_size)

        self._row_size = QtW.QSpinBox()
        self._row_size.setRange(10, 100)
        self._row_size.setValue(cfg.table.row_size)

        self._column_size = QtW.QSpinBox()
        self._column_size.setRange(20, 200)
        self._column_size.setValue(cfg.table.column_size)

        _layout = QtW.QFormLayout()
        _layout.addRow("Max row count", self._max_row_count)
        _layout.addRow("Max column count", self._max_column_count)
        _layout.addRow("Font family", self._font)
        _layout.addRow("Font size", self._font_size)
        _layout.addRow("Default row span", self._row_size)
        _layout.addRow("Default column span", self._column_size)

        self._max_row_count.valueChanged.connect(self._throttler.throttle)
        self._max_column_count.valueChanged.connect(self._throttler.throttle)
        self._font.currentFontChanged.connect(self._throttler.throttle)
        self._font_size.valueChanged.connect(self._throttler.throttle)
        self._row_size.valueChanged.connect(self._throttler.throttle)
        self._column_size.valueChanged.connect(self._throttler.throttle)

        self.setLayout(_layout)
