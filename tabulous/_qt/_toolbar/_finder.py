from __future__ import annotations
from typing import Iterator
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Signal, Qt

from . import _utils


class QFinderWidget(QtW.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        _layout = QtW.QHBoxLayout()
        self._search_box = QSearchBox()
        self._search_box.enterClicked.connect(self.findNext)
        self._search_box.textChanged.connect(self.initSearchBox)
        _layout.addWidget(self._search_box)
        self.setLayout(_layout)
        self._qtable_viewer = _utils.find_parent_table_viewer(self)
        self._current_iterator: Iterator[tuple[int, int]] | None = None
        self._find_method = "row"

    def searchBox(self) -> QSearchBox:
        return self._search_box

    def initSearchBox(self, text: str):
        if self._find_method == "row":
            self._current_iterator = self._iter_find_rowwise(text)
        else:
            self._current_iterator = self._iter_find_columnwise(text)

    def findNext(self) -> None:
        text = self._search_box.text()
        if not text:
            return
        try:
            r, c = next(self._current_iterator)
        except StopIteration:
            self.initSearchBox(text)
            return
        qtable = self.currentTable()
        qtable.moveToItem(r + 2, c + 2)
        qtable.moveToItem(r, c)
        qtable.setSelections([(r, c)])
        return

    def currentTable(self):
        tablestack = self._qtable_viewer._tablestack
        idx = tablestack.currentIndex()
        return tablestack.tableAtIndex(idx)

    def _iter_find_rowwise(self, text: str):
        qtable = self.currentTable()
        df = qtable.model().df
        for r, (_, row) in enumerate(df.iterrows()):
            for c, item in enumerate(row):
                if qtable is not self.currentTable():
                    return
                try:
                    val = qtable.convertValue(0, c, text)
                except Exception:
                    continue
                if item == val:
                    yield r, c

    def _iter_find_columnwise(self, text: str):
        qtable = self.currentTable()
        df = qtable.model().df
        for c, (_, col) in enumerate(df.iteritems()):
            try:
                val = qtable.convertValue(0, c, text)
            except Exception:
                continue
            for r, item in enumerate(col):
                if qtable is not self.currentTable():
                    return
                if item == val:
                    yield r, c


class QSearchBox(QtW.QLineEdit):
    enterClicked = Signal()
    escClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        from ..._global_variables import table

        self.setFont(QtGui.QFont(table.font, table.font_size))

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key.Key_Return:
            self.enterClicked.emit()
        elif event.key() == Qt.Key.Key_Escape:
            self.escClicked.emit()
        else:
            super().keyPressEvent(event)
