from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui


class QTableConfigPanel(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)

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
        self._font.setFont(QtGui.QFont(cfg.table.font))

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
        _layout.addRow("Row span", self._row_size)
        _layout.addRow("Column span", self._column_size)

        self.setLayout(_layout)
