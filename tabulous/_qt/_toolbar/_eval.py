from __future__ import annotations
from qtpy import QtWidgets as QtW
import pandas as pd
from . import _utils


class QLiteralEvalWidget(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._label = QtW.QLabel(">>>", self)
        self._line = _utils.QCompletableLineEdit(self)
        self._btn = QtW.QPushButton("Eval")
        self._btn.clicked.connect(self.eval)
        self._line.enterClicked.connect(self.eval)

        _layout = QtW.QHBoxLayout()
        _layout.addWidget(self._label)
        _layout.addWidget(self._line)
        _layout.addWidget(self._btn)
        self.setLayout(_layout)

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


class QLiteralFilterWidget(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._label = QtW.QLabel(">>>", self)
        self._line = _utils.QCompletableLineEdit(self)
        self._btn = QtW.QPushButton("Filter")
        self._btn.clicked.connect(self.filter)
        self._line.enterClicked.connect(self.filter)

        _layout = QtW.QHBoxLayout()
        _layout.addWidget(self._label)
        _layout.addWidget(self._line)
        _layout.addWidget(self._btn)
        self.setLayout(_layout)

    def filter(self):
        """Update the filter of the current table using the expression."""
        text = self._line.text()
        if text == "":
            return
        table = self._line.currentPyTable()
        sl = table.data.eval(text, inplace=False)
        table.filter = EvalArray(sl, literal=text)
        self._line.toHistory()


class EvalArray(pd.Series):
    def __init__(self, data=None, literal: str = ""):
        super().__init__(data)
        self._literal = literal

    def __repr__(self):
        return f"lambda df: df.eval({self._literal!r})"
