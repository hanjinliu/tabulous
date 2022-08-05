from __future__ import annotations
from typing import TYPE_CHECKING
import re
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Signal, Qt

from . import _utils

if TYPE_CHECKING:
    from ...widgets.mainwindow import TableViewerBase
    from .._table._base import DataFrameModel

_OPERATORS = re.compile(r"\+|-|\*|/|\s|\(|\)|%|<|>|=")


class QLiteralEval(QtW.QLineEdit):
    enterClicked = Signal()
    escClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        from ..._global_variables import table

        self.setFont(QtGui.QFont(table.font, table.font_size))
        self._qtable_viewer = _utils.find_parent_table_viewer(self)
        self.enterClicked.connect(self.eval)
        self.textChanged.connect(self.setCompletion)

    def eval(self):
        text = self.text()
        table = self.currentPyTable()
        df = table.data.eval(text, inplace=False)
        if "=" not in text:
            return self._qtable_viewer._table_viewer.add_table(df, name=table.name)
        new_col_name = text.split("=")[0].strip()
        table._qwidget.assignColumn(df[new_col_name])

    def currentQTable(self):
        tablestack = self._qtable_viewer._tablestack
        idx = tablestack.currentIndex()
        return tablestack.tableAtIndex(idx)

    def currentPyTable(self):
        viewer = self._qtable_viewer._table_viewer
        return viewer.current_table

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Return:
            self.enterClicked.emit()
        elif key == Qt.Key.Key_Escape:
            self.escClicked.emit()
        elif key == Qt.Key.Key_Tab:
            self.setSelection(len(self.text()), len(self.text()))
        else:
            self._last_key = key
            super().keyPressEvent(event)

    def setCompletion(self, text: str):
        """Set auto completion for the text in the line edit."""
        if self._last_key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            # don't autocomplete if the user deleted a character
            return

        last_word = _OPERATORS.split(text)[-1].strip()
        if not last_word.isidentifier():
            return
        matched: list[str] = []
        for name in self.currentPyTable().data.columns:
            name = str(name)
            if name.startswith(last_word):
                matched.append(name)

        if not matched:
            return

        matched.sort()
        _to_complete = matched[0].lstrip(last_word)
        new_text = text + _to_complete
        self.setText(new_text)
        self.setCursorPosition(len(text))
        self.setSelection(len(text), len(new_text))
