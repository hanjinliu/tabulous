from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt

if TYPE_CHECKING:
    from tabulous._qt._mainwindow import _QtMainWidgetBase


class QIntOrEmptyValidator(QtGui.QIntValidator):
    def validate(self, input: str, pos: int) -> tuple[QtGui.QValidator.State, str, int]:
        if input == "":
            return QtGui.QValidator.State.Acceptable, input, pos
        return super().validate(input, pos)


class QJumpWidget(QtW.QDialog):
    """Implements the jump-to behavior."""

    def __init__(self, parent: _QtMainWidgetBase | None = None) -> None:
        super().__init__(parent, Qt.WindowType.SubWindow)
        _line_edits = QtW.QWidget()
        self._msg = QtW.QLabel("")

        self._row = QtW.QLineEdit()
        self._row.setToolTip("Row index")
        self._col = QtW.QLineEdit()
        self._col.setToolTip("Column index")
        idx = parent._table_viewer.current_table.current_index
        self._row.setText(str(idx[0]))
        self._col.setText(str(idx[1]))
        self._row.setValidator(QIntOrEmptyValidator())
        self._col.setValidator(QIntOrEmptyValidator())

        self._row.textChanged.connect(self._on_text_changed)
        self._col.textChanged.connect(self._on_text_changed)
        _hbox = QtW.QHBoxLayout()
        _hbox.addWidget(self._row)
        _hbox.addWidget(QtW.QLabel(", "))
        _hbox.addWidget(self._col)
        _hbox.setContentsMargins(0, 0, 0, 0)
        _line_edits.setLayout(_hbox)

        _vbox = QtW.QVBoxLayout()
        _vbox.addWidget(QtW.QLabel("Jump to:"))
        _vbox.addWidget(_line_edits)
        _vbox.addWidget(self._msg)
        self.setLayout(_vbox)

        self._row.editingFinished.connect(self._on_row_finished)
        self._col.editingFinished.connect(self._on_col_finished)
        self._last_valid_row, self._last_valid_col = idx

        # move to the center of the parent
        self.resize(240, 100)
        self.move(parent.rect().center() - self.rect().center())

    def _delete(self):
        self.hide()
        self.deleteLater()

    def _on_row_finished(self):
        self._col.setFocus()
        self._col.selectAll()
        if not self._col.hasFocus():
            self._delete()

    def _on_col_finished(self):
        self.parentWidget().setCellFocus()
        if not self._row.hasFocus():
            self._delete()

    def _on_text_changed(self):
        rtext = self._row.text()
        ctext = self._col.text()
        if rtext == "":
            r = self._last_valid_row
        else:
            self._last_valid_row = r = int(rtext)
        if ctext == "":
            c = self._last_valid_col
        else:
            self._last_valid_col = c = int(ctext)

        table = self.parentWidget()._table_viewer.current_table
        if r < table.table_shape[0] and c < table.table_shape[1]:
            table.move_iloc(r, c)
            self._msg.setText("")
        else:
            self._msg.setText(f"Index out of bound: ({r}, {c})")

    def parentWidget(self) -> _QtMainWidgetBase:
        return super().parentWidget()

    def show(self):
        super().show()
        self._row.selectAll()
        self._row.setFocus()
