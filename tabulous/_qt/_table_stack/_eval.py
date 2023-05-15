from __future__ import annotations
from qtpy import QtWidgets as QtW
from . import _utils


class QAbstractEval(QtW.QWidget):
    _BUTTON_TEXT = ""
    _PLACEHOLDER_TEXT = ""

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._label = QtW.QLabel(">>>", self)
        self._line = _utils.QCompletableLineEdit(self)
        self._btn = QtW.QPushButton(self._BUTTON_TEXT)
        self._btn.clicked.connect(self.callback)
        self._line.enterClicked.connect(self.callback)
        self._line.setPlaceholderText(self._PLACEHOLDER_TEXT)

        _layout = QtW.QHBoxLayout()
        _layout.addWidget(self._label)
        _layout.addWidget(self._line)
        _layout.addWidget(self._btn)
        self.setLayout(_layout)

        self.setToolTip(self.__class__.__doc__.replace("\n    ", "\n").strip())

    def callback(self):
        raise NotImplementedError()

    def lineEdit(self) -> QtW.QLineEdit:
        return self._line


class QLiteralEvalWidget(QAbstractEval):
    """
    Evaluate literal string.

    >>> result = val * 3  # Update or create "result" column
    >>> val_norm = val - val.mean()  # Use DataFrame method
    """

    _BUTTON_TEXT = "Eval"
    _PLACEHOLDER_TEXT = "e.g. result = val * 3"

    def callback(self):
        """Evaluate the current text as a Python expression."""
        text = self._line.text()
        if text == "":
            return
        table = self._line.currentPyTable(assert_mutable=True)
        table.query(text)
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
    _PLACEHOLDER_TEXT = "e.g. length < 3.5"

    def callback(self):
        """Update the filter of the current table using the expression."""
        text = self._line.text()
        if text == "":
            return
        table = self._line.currentPyTable()
        table.proxy.filter(text)
        self._line.toHistory()
