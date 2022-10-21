from __future__ import annotations
import ast
from qtpy import QtWidgets as QtW
import pandas as pd
from . import _utils


class QAbstractEval(QtW.QWidget):
    _BUTTON_TEXT = ""

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._label = QtW.QLabel(">>>", self)
        self._line = _utils.QCompletableLineEdit(self)
        self._btn = QtW.QPushButton(self._BUTTON_TEXT)
        self._btn.clicked.connect(self.callback)
        self._line.enterClicked.connect(self.callback)

        _layout = QtW.QHBoxLayout()
        _layout.addWidget(self._label)
        _layout.addWidget(self._line)
        _layout.addWidget(self._btn)
        self.setLayout(_layout)

        self.setToolTip(self.__class__.__doc__.replace("\n    ", "\n").strip())

    def callback(self):
        raise NotImplementedError()


class QLiteralEvalWidget(QAbstractEval):
    """
    Evaluate literal string.

    >>> result = val * 3  # Update or create "result" column
    >>> val_norm = val - val.mean()  # Use DataFrame method
    """

    _BUTTON_TEXT = "Eval"

    def callback(self):
        """Evaluate the current text as a Python expression."""
        text = self._line.text()
        if text == "":
            return
        table = self._line.currentPyTable()
        df = table.data.eval(text, inplace=False, global_dict={"df": table.data})
        if type(ast.parse(text.replace("@", "")).body[0]) is not ast.Assign:
            self._line._qtable_viewer._table_viewer.add_table(df, name=table.name)
        else:
            table.data = df  # TODO: this is massive. Should use assignColumn().
            table.move_iloc(None, -1)
        self._line.toHistory()


class QLiteralFilterWidget(QAbstractEval):
    """
    Apply filter using literal string.

    Examples
    --------
    >>> variable < 1.4  # values in "variable" column is < 1.4
    >>> a < b  # values in "a" column < values in "b" column
    >>> None  # reset filter
    """

    _BUTTON_TEXT = "Filter"

    def callback(self):
        """Update the filter of the current table using the expression."""
        text = self._line.text()
        if text == "":
            return
        table = self._line.currentPyTable()
        sl = table.data.eval(text, inplace=False)
        if isinstance(sl, pd.Series):
            table.filter = EvalArray(sl, literal=text)
        else:
            table.filter = sl
        self._line.toHistory()


class EvalArray(pd.Series):
    def __init__(self, data=None, literal: str = ""):
        super().__init__(data)
        self._literal = literal

    def __repr__(self):
        return f"lambda df: df.eval({self._literal!r})"
