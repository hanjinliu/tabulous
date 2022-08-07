from __future__ import annotations
from qtpy import QtWidgets as QtW
from . import _utils


class QLiteralEval(QtW.QWidget):
    def __init__(self, parent=None, label="", mode="eval"):
        super().__init__(parent)
        self._label = QtW.QLabel(label, self)
        self._line = _utils.QCompletableLineEdit(self)
        self.setMode(mode)

    def eval(self):
        """Evaluate the current text as a Python expression."""
        text = self._line.text()
        if text == "":
            return
        table = self._line.currentPyTable()
        df = table.data.eval(text, inplace=False)
        if "=" not in text:
            self._line._qtable_viewer._table_viewer.add_table(df, name=table.name)
        else:
            table.data = df  # TODO: this is massive. Should use assignColumn().
            table.move_iloc(None, -1)
        self._line.toHistory()

    def filter(self):
        """Update the filter of the current table using the expression."""
        text = self._line.text()
        if text == "":
            return
        table = self._line.currentPyTable()
        sl = table.data.eval(text, inplace=False)
        table.filter = sl
        self._line.toHistory()

    def query(self):
        """Add a filtrated data of the current table using the expression."""
        text = self._line.text()
        if text == "":
            return
        table = self._line.currentPyTable()
        sl = table.data.eval(text, inplace=False)
        self._line._qtable_viewer._table_viewer.add_table(
            table.data[sl], name=table.name
        )
        self._line.toHistory()

    def setMode(self, mode: str):
        try:
            self._line.enterClicked.disconnect()
        except TypeError:
            pass
        if mode == "eval":
            self._line.enterClicked.connect(self.eval)
        elif mode == "filter":
            self._line.enterClicked.connect(self.filter)
        elif mode == "query":
            self._line.enterClicked.connect(self.query)
        else:
            raise ValueError(mode)
