from __future__ import annotations
from typing import Iterator, TYPE_CHECKING
import re
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Signal, Qt

from . import _utils

if TYPE_CHECKING:
    from .._table import QBaseTable


class MatchMode:
    value = "12"
    text = "'12'"
    text_partial = "'1'2"
    regex = ".*"


class QComboButtons(QtW.QWidget):
    """Collection of buttons to choose between match modes"""

    currentTextChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        choices = [
            MatchMode.value,
            MatchMode.text,
            MatchMode.text_partial,
            MatchMode.regex,
        ]
        _layout = QtW.QHBoxLayout()
        _layout.setContentsMargins(0, 0, 0, 0)
        _layout.setSpacing(2)
        self.setLayout(_layout)
        buttons = [QtW.QPushButton(choice, self) for choice in choices]
        buttons[0].setToolTip("Match by value")
        buttons[1].setToolTip("Match by text")
        buttons[2].setToolTip("Partial match by text")
        buttons[3].setToolTip("Match by regular expression")

        for i, btn in enumerate(buttons):
            _layout.addWidget(btn)
            btn.setCheckable(True)
            btn.setFont(QtGui.QFont("Arial"))
            btn.setFixedSize(32, 18)
            btn.clicked.connect(lambda checked, idx=i: self.setCurrentIndex(idx))

        self._buttons = buttons
        self.setCurrentIndex(0)

    def currentIndex(self) -> int:
        """Currently selected index."""
        for i, btn in enumerate(self._buttons):
            if btn.isChecked():
                return i
        return -1

    def setCurrentIndex(self, index: int) -> None:
        """Set currently selected index."""
        for i, btn in enumerate(self._buttons):
            checked = i == index
            btn.setChecked(checked)
            font = btn.font()
            font.setBold(checked)
            btn.setFont(font)
        text = self._buttons[index].text()
        self.currentTextChanged.emit(text)


class QFinderWidget(QtW.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        _layout = QtW.QVBoxLayout()
        self._search_box = QSearchBox()
        self._search_box.enterClicked.connect(self.findNext)
        self._search_box.textChanged.connect(self.initSearchBox)
        _search_box_widget = QWithButton(self._search_box, text="Find")
        _search_box_widget.clicked.connect(self.findNext)
        _layout.addWidget(_search_box_widget)

        self._replace_box = QSearchBox()
        self._replace_box.enterClicked.connect(self.replaceCurrent)
        _replace_box_widget = QWithButton(self._replace_box, text="Replace")
        _layout.addWidget(_replace_box_widget)
        _replace_box_widget.clicked.connect(self.replaceCurrent)

        _footer = QtW.QWidget()
        _layout.addWidget(_footer)
        _footer.setLayout(QtW.QHBoxLayout())
        _footer.layout().setContentsMargins(0, 0, 0, 0)

        self.cbox_match = QComboButtons()
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
        self._current_index = None

    def searchBox(self) -> QSearchBox:
        return self._search_box

    def replaceBox(self) -> QSearchBox:
        return self._replace_box

    def setReplaceBoxVisible(self, visible: bool):
        return self._replace_box.parentWidget().setVisible(visible)

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
        self._current_index = (r, c)
        return

    def replaceCurrent(self) -> None:
        """Replace the current cell with the text in the box"""
        if self._current_index is None or not self._replace_box.isVisible():
            return
        qtable = self.currentTable()
        r, c = self._current_index
        value = qtable.convertValue(r, c, self._replace_box.text())
        qtable.setDataFrameValue(r, c, value)
        return self.findNext()

    def setMatchMode(self, mode: str):
        if mode == MatchMode.value:
            self._match_method = self._value_match
        elif mode == MatchMode.text:
            self._match_method = self._text_match
        elif mode == MatchMode.text_partial:
            self._match_method = self._text_partial_match
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

    def _text_partial_match(
        self, qtable: QBaseTable, r: int, c: int, item, text: str
    ) -> bool:
        return text in str(item)

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


class QWithButton(QtW.QWidget):
    clicked = Signal()

    def __init__(self, widget: QtW.QLineEdit, text: str = "...") -> None:
        super().__init__()
        _layout = QtW.QHBoxLayout()
        _layout.setContentsMargins(0, 0, 0, 0)
        _layout.addWidget(widget)
        self._btn = QtW.QPushButton(text)
        _layout.addWidget(self._btn)
        self.setLayout(_layout)
        self._btn.clicked.connect(lambda: self.clicked.emit())

    def button(self) -> QtW.QPushButton:
        return self._btn
