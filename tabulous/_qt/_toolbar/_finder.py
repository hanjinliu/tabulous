from __future__ import annotations
from typing import Iterator, TYPE_CHECKING
import re
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Signal, Qt

from . import _utils

if TYPE_CHECKING:
    from .._table import QBaseTable


class MatchMode:
    value = "a/1"
    text = "'a'/'1'"
    regex = ".*"


class QFinderWidget(QtW.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        _layout = QtW.QVBoxLayout()
        self._search_box = QSearchBox()
        self._search_box.enterClicked.connect(self.findNext)
        self._search_box.textChanged.connect(self.initSearchBox)
        _layout.addWidget(self._search_box)

        _footer = QtW.QWidget()
        _layout.addWidget(_footer)
        _footer.setLayout(QtW.QHBoxLayout())
        _footer.layout().setContentsMargins(0, 0, 0, 0)

        self.cbox_match = QtW.QComboBox()
        self.cbox_match.addItems([MatchMode.value, MatchMode.text, MatchMode.regex])
        self.cbox_match.setCurrentIndex(0)
        self.cbox_match.currentTextChanged.connect(self.setMatchMode)

        self.cbox_ori = QtW.QComboBox()
        self.cbox_ori.addItems(["row", "column"])
        self.cbox_ori.setCurrentIndex(1)
        self.cbox_ori.currentTextChanged.connect(self.setFindOrientation)

        _footer.layout().addWidget(self.cbox_ori)
        _footer.layout().addWidget(self.cbox_match)

        self.setLayout(_layout)
        self._qtable_viewer = _utils.find_parent_table_viewer(self)
        self._current_iterator: Iterator[tuple[int, int]] | None = None
        self.setFindOrientation("column")
        self.setMatchMode(MatchMode.value)

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

    def setMatchMode(self, mode: str):
        if mode == MatchMode.value:
            self._match_method = self._value_match
        elif mode == MatchMode.text:
            self._match_method = self._text_match
        elif mode == MatchMode.regex:
            self._match_method = self._text_regex_match
        else:
            raise ValueError(f"Unknown match mode: {mode}")

    def setFindOrientation(self, ori: str):
        if ori == "row":
            self._find_method = "row"
        elif ori == "column":
            self._find_method = "column"
        else:
            raise ValueError(f"Unknown orientation: {ori}")

    def currentTable(self) -> QBaseTable:
        tablestack = self._qtable_viewer._tablestack
        idx = tablestack.currentIndex()
        return tablestack.tableAtIndex(idx)

    def _iter_find_rowwise(self, text: str):
        qtable = self.currentTable()
        df = qtable.dataShown()
        for r, (_, row) in enumerate(df.iterrows()):
            for c, item in enumerate(row):
                if self._match_method(qtable, r, c, item, text):
                    yield r, c
                    if qtable is not self.currentTable():
                        return

    def _iter_find_columnwise(self, text: str):
        qtable = self.currentTable()
        df = qtable.dataShown()
        for c, (_, col) in enumerate(df.iteritems()):
            try:
                qtable.convertValue(0, c, text)
            except Exception:
                continue
            for r, item in enumerate(col):
                if self._match_method(qtable, r, c, item, text):
                    yield r, c
                    if qtable is not self.currentTable():
                        # if user changed the table.
                        return

    def _value_match(self, qtable: QBaseTable, r: int, c: int, item, text: str) -> bool:
        try:
            val = qtable.convertValue(r, c, text)
        except Exception:
            return False
        return item == val

    def _text_match(self, qtable: QBaseTable, r: int, c: int, item, text: str) -> bool:
        model = qtable.model()
        index = model.index(r, c)
        data = qtable.model().data(index, Qt.ItemDataRole.DisplayRole)
        displayed_text = qtable.itemDelegate()._format_number(data)
        return displayed_text == text

    def _text_regex_match(
        self, qtable: QBaseTable, r: int, c: int, item, text: str
    ) -> bool:
        return re.match(text, str(item)) is not None


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
