from __future__ import annotations
import re
from typing import TYPE_CHECKING, cast
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Signal, Qt

if TYPE_CHECKING:
    from .._mainwindow import _QtMainWidgetBase


def create_temporal_line_edit(
    rect: QtCore.QRect,
    parent: QtW.QWidget,
    text: str,
) -> QtW.QLineEdit:
    line = QtW.QLineEdit(parent=parent)
    geometry = line.geometry()
    geometry.setWidth(rect.width())
    geometry.setHeight(rect.height())
    geometry.moveCenter(rect.center())
    geometry.adjust(4, 4, -2, -2)
    line.setGeometry(geometry)
    line.setText(text)
    line.setHidden(False)
    line.setFocus()
    line.selectAll()
    return line


def find_parent_table_viewer(qwidget: _QtMainWidgetBase) -> _QtMainWidgetBase:
    x = qwidget
    while (parent := x.parent()) is not None:
        x = parent
        if hasattr(x, "_table_viewer"):
            return x
    raise RuntimeError


_OPERATORS = re.compile(r"\+|-|\*|/|\s|\(|\)|%|<|>|=")


class _EventFilter(QtCore.QObject):
    """An event filter for text completion by tab."""

    def eventFilter(self, o: QtCore.QObject, e: QtCore.QEvent):
        if e.type() == QtCore.QEvent.Type.KeyPress:
            e = cast(QtGui.QKeyEvent, e)
            if e.key() == Qt.Key.Key_Tab:
                l = cast(QCompletableLineEdit, self.parent())
                l.setSelection(len(l.text()), len(l.text()))
                return True
        return False


class QCompletableLineEdit(QtW.QLineEdit):
    """A QLineEdit implemented with completion."""

    enterClicked = Signal()
    escClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        from ..._global_variables import get_table_setting

        st = get_table_setting()

        font = QtGui.QFont(st.font, st.font_size)
        self.setFont(font)
        self._qtable_viewer = find_parent_table_viewer(self)
        self.textChanged.connect(self.setCompletion)
        self._history: list[str] = []
        self._history_pos: int = -1
        self._event_filter = _EventFilter(self)
        self.installEventFilter(self._event_filter)

    def currentQTable(self):
        tablestack = self._qtable_viewer._tablestack
        idx = tablestack.currentIndex()
        return tablestack.tableAtIndex(idx)

    def currentPyTable(self):
        viewer = self._qtable_viewer._table_viewer
        return viewer.current_table

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        self._last_key = key
        if key == Qt.Key.Key_Return:
            self.enterClicked.emit()
        elif key == Qt.Key.Key_Escape:
            self.escClicked.emit()
        elif key == Qt.Key.Key_Tab:
            self.setSelection(len(self.text()), len(self.text()))
        elif key == Qt.Key.Key_Up and self._history:
            self._history_pos -= 1
            if self._history_pos < 0:
                self._history_pos = 0
            self.setText(self._history[self._history_pos])

        elif key == Qt.Key.Key_Down:
            if self._history_pos == len(self._history):
                return
            self._history_pos += 1
            if self._history_pos == len(self._history):
                self.setText("")
            else:
                self.setText(self._history[self._history_pos])
        else:
            super().keyPressEvent(event)

    def toHistory(self):
        self._history.append(self.text())
        if len(self._history) > 300:
            self._history = self._history[-300:]
        self.setText("")
        self._history_pos = len(self._history)

    def setCompletion(self, text: str):
        """Set auto completion for the text in the line edit."""
        if self._last_key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            # don't autocomplete if the user deleted a character
            return

        elif self.cursorPosition() < len(self.text()):
            return

        new_text = _complete(text, self.currentPyTable().data.columns)
        if new_text is not None:
            self.blockSignals(True)
            self.setText(new_text)
            self.blockSignals(False)
            self.setCursorPosition(len(text))
            self.setSelection(len(text), len(new_text))


def _complete(text: str, words: list) -> str | None:
    last_word = _OPERATORS.split(text)[-1].strip()
    if not last_word.isidentifier():
        return
    matched: list[str] = []
    for name in words:
        name = str(name)
        if name.startswith(last_word):
            matched.append(name)

    if not matched:
        return None

    matched.sort()
    _to_complete = matched[0][len(last_word) :]
    return text + _to_complete
