from __future__ import annotations
from typing import Callable, TYPE_CHECKING
from functools import partial
from abc import ABC, abstractmethod
import re
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Signal, Qt

from . import _utils

if TYPE_CHECKING:
    from .._table import QBaseTable


class MatchMode:
    """Match mode for search"""

    value = "12"
    text = "'12'"
    text_partial = "'1'2"
    regex = ".*"
    expr = ">>>"


class SearchOrientation:
    """Orientation of searching"""

    row = "⇉"
    column = "⇊"


class QComboButtons(QtW.QWidget):
    """Collection of buttons to choose between match modes"""

    currentTextChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        choices = list(
            v for k, v in MatchMode.__dict__.items() if not k.startswith("_")
        )
        _layout = QtW.QHBoxLayout()
        _layout.setContentsMargins(0, 0, 0, 0)
        _layout.setSpacing(2)
        self.setLayout(_layout)
        buttons = [QtW.QPushButton(choice, self) for choice in choices]
        buttons[0].setToolTip("Match by value")
        buttons[1].setToolTip("Match by text")
        buttons[2].setToolTip("Partial match by text")
        buttons[3].setToolTip("Match by regular expression")
        buttons[4].setToolTip("Match by any expression")

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
        _search_box_widget = QWithButtons(self._search_box, texts=["↑", "↓"])
        _search_box_widget.clicked.connect(
            lambda i: self.findPrevious() if i == 0 else self.findNext()
        )
        _search_box_widget.button(0).setToolTip("Find next")
        _search_box_widget.button(1).setToolTip("Find previous")
        _layout.addWidget(_search_box_widget)

        self._replace_box = QSearchBox()
        self._replace_box.enterClicked.connect(self.replaceCurrent)
        _replace_box_widget = QWithButtons(self._replace_box, texts=["↵", "↵↵"])
        _replace_box_widget.button(0).setToolTip("Replace current item")
        _replace_box_widget.button(1).setToolTip("Replace all items")
        _layout.addWidget(_replace_box_widget)
        _replace_box_widget.clicked.connect(
            lambda i: self.replaceCurrent() if i == 0 else self.replaceAll()
        )

        policy = (QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed)
        self._search_box.setSizePolicy(*policy)
        self._replace_box.setSizePolicy(*policy)

        _footer = QtW.QWidget()
        _layout.addWidget(_footer)
        _footer.setLayout(QtW.QHBoxLayout())
        _footer.layout().setContentsMargins(0, 0, 0, 0)

        self.cbox_match = QComboButtons()
        self.cbox_match.currentTextChanged.connect(self.setMatchMode)

        self.cbox_ori = QtW.QComboBox()
        self.cbox_ori.addItems([SearchOrientation.row, SearchOrientation.column])
        self.cbox_ori.setCurrentIndex(1)
        self.cbox_ori.currentTextChanged.connect(self.initSearchBox)

        _footer.layout().addWidget(self.cbox_ori)
        _footer.layout().addWidget(self.cbox_match)

        self.setLayout(_layout)
        self._qtable_viewer = _utils.find_parent_table_viewer(self)
        self._current_iterator: TwoWayIterator | None = None

        self.setMatchMode(MatchMode.value)
        self._current_index = None

    def searchBox(self) -> QSearchBox:
        return self._search_box

    def replaceBox(self) -> QSearchBox:
        return self._replace_box

    def setReplaceBoxVisible(self, visible: bool):
        return self._replace_box.parentWidget().setVisible(visible)

    def initSearchBox(self):
        if self.cbox_ori.currentText() == SearchOrientation.row:
            self._current_iterator = RowwiseIterator(self.currentTable().dataShape())
        else:
            self._current_iterator = ColumnwiseIterator(self.currentTable().dataShape())
        if self._current_index is not None:
            self._current_iterator.set_index(*self._current_index)

    def findNext(self) -> None:
        """Find next item that match in the current mode."""
        text = self._search_box.text()
        if not text:
            return
        qtable = self.currentTable()
        pf = partial(self._match_method, qtable, text)
        self._current_iterator.shape = qtable.dataShape()

        try:
            r, c = self._current_iterator.next_until(pf)
        except ItemNotFound:
            raise ItemNotFound(f"{text!r} not found.")
        qtable = self.currentTable()
        qtable.moveToItem(r + 2, c + 2)
        qtable.moveToItem(r, c)
        qtable.setSelections([(r, c)])
        self._current_index = (r, c)
        return

    def findPrevious(self) -> None:
        """Find previous item that match in the current mode."""
        text = self._search_box.text()
        if not text:
            return
        qtable = self.currentTable()
        pf = partial(self._match_method, qtable, text)
        self._current_iterator.shape = qtable.dataShape()

        try:
            r, c = self._current_iterator.prev_until(pf)
        except ItemNotFound:
            raise ItemNotFound(f"{text!r} not found.")
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
        convert_value = qtable._get_converter(c)
        value = convert_value(c, self._replace_box.text())
        qtable.setDataFrameValue(r, c, value)
        return self.findNext()

    def replaceAll(self) -> None:
        """Replace all matching cells with the text in the box"""
        text = self._search_box.text()
        text_after = self._replace_box.text()
        if not text:
            return
        self.initSearchBox()
        qtable = self.currentTable()
        pf = partial(self._match_method, qtable, text)
        self._current_iterator.shape = qtable.dataShape()

        with qtable._mgr.merging(lambda cmd: f"Replace {text!r} to {text_after!r}"):
            while True:
                try:
                    r, c = self._current_iterator.next_until(pf)
                except ItemNotFound:
                    self.initSearchBox()
                    break
                convert_value = qtable._get_converter(c)
                value = convert_value(c, text_after)
                qtable.setDataFrameValue(r, c, value)

        return None

    def setMatchMode(self, mode: str):
        """Set the match mode and update match function."""
        if mode == MatchMode.value:
            self._match_method = self._value_match
        elif mode == MatchMode.text:
            self._match_method = self._text_match
        elif mode == MatchMode.text_partial:
            self._match_method = self._text_partial_match
        elif mode == MatchMode.regex:
            self._match_method = self._text_regex_match
        elif mode == MatchMode.expr:
            self._match_method = self._expr_match
        else:
            raise ValueError(f"Unknown match mode: {mode}")

    def currentTable(self) -> QBaseTable:
        tablestack = self._qtable_viewer._tablestack
        idx = tablestack.currentIndex()
        return tablestack.tableAtIndex(idx)

    def _value_match(self, qtable: QBaseTable, text: str, r: int, c: int) -> bool:
        try:
            val = qtable.convertValue(c, text)
        except Exception:
            return False
        return qtable.dataShown().iloc[r, c] == val

    def _text_match(self, qtable: QBaseTable, text: str, r: int, c: int) -> bool:
        model = qtable.model()
        index = model.index(r, c)
        displayed_text = qtable.model().data(index, Qt.ItemDataRole.DisplayRole)
        return displayed_text == text

    def _text_partial_match(
        self, qtable: QBaseTable, text: str, r: int, c: int
    ) -> bool:
        return text in str(qtable.dataShown().iloc[r, c])

    def _text_regex_match(self, qtable: QBaseTable, text: str, r: int, c: int) -> bool:
        return re.match(text, str(qtable.dataShown().iloc[r, c])) is not None

    def _expr_match(self, qtable: QBaseTable, text: str, r: int, c: int) -> bool:
        import numpy, pandas

        f = eval(f"(lambda x: {text})", {"np": numpy, "pd": pandas}, {})
        try:
            return f(qtable.dataShown().iloc[r, c])
        except Exception:
            return False


class QSearchBox(QtW.QLineEdit):
    enterClicked = Signal()
    escClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        from ..._utils import get_config

        table_config = get_config().table
        self.setFont(QtGui.QFont(table_config.font, table_config.font_size))

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key.Key_Return:
            self.enterClicked.emit()
        elif event.key() == Qt.Key.Key_Escape:
            self.escClicked.emit()
        else:
            super().keyPressEvent(event)


class QWithButtons(QtW.QWidget):
    """A container widget that contains a line edit and a button."""

    clicked = Signal(int)

    def __init__(self, widget: QtW.QLineEdit, texts: list[str]) -> None:
        super().__init__()
        _layout = QtW.QHBoxLayout()
        _layout.setContentsMargins(0, 0, 0, 0)
        _layout.addWidget(widget)
        self._buttons = []
        for i, text in enumerate(texts):
            btn = self._make_button(i, text)
            _layout.addWidget(btn)
            self._buttons.append(btn)

        self.setLayout(_layout)

    def _make_button(self, i: int, text: str):
        btn = QtW.QPushButton(text)
        btn.clicked.connect(lambda: self.clicked.emit(i))
        btn.setFixedWidth(36)
        return btn

    def button(self, idx: int) -> QtW.QPushButton:
        """Get the button at the given index."""
        return self._buttons[idx]


class ItemNotFound(Exception):
    """Raised when the item is not found."""


class TwoWayIterator(ABC):
    def __init__(self, shape: tuple[int, int]):
        self.shape = shape
        self.go_to_first()

    def set_index(self, r: int, c: int) -> None:
        self._r = r
        self._c = c
        return None

    @abstractmethod
    def go_to_first(self) -> None:
        """Go to the first index."""

    @abstractmethod
    def go_to_last(self) -> None:
        """Go to the last index."""

    @abstractmethod
    def next(self):
        """Next item."""

    @abstractmethod
    def prev(self):
        """Previous item."""

    def next_until(self, predicate: Callable[[int, int], bool]) -> tuple[int, int]:
        """Next item until the predicate is True."""
        start = item = self.next()
        while True:
            if predicate(*item):
                return item
            item = self.next()
            if item == start:
                raise ItemNotFound

    def prev_until(self, predicate: Callable[[int, int], bool]) -> tuple[int, int]:
        """Next item until the predicate is True."""
        start = item = self.prev()
        while True:
            if predicate(*item):
                return item
            item = self.prev()
            if item == start:
                raise ItemNotFound


class RowwiseIterator(TwoWayIterator):
    def go_to_first(self) -> None:
        self._r = 0
        self._c = -1

    def go_to_last(self) -> None:
        self._r = self.shape[0] - 1
        self._c = self.shape[1]

    def next(self) -> tuple[int, int]:
        self._c += 1
        nr, nc = self.shape
        if self._c >= nc:
            self._c = 0
            self._r += 1
            if self._r >= nr:
                self.go_to_first()
                self._c += 1
        return self._r, self._c

    def prev(self) -> tuple[int, int]:
        self._c -= 1
        if self._c < 0:
            nr, nc = self.shape
            self._c = nc - 1
            self._r -= 1
            if self._r < 0:
                self.go_to_last()
                self._c -= 1
        return self._r, self._c


class ColumnwiseIterator(TwoWayIterator):
    def go_to_first(self) -> None:
        self._r = -1
        self._c = 0

    def go_to_last(self) -> None:
        self._r = self.shape[0]
        self._c = self.shape[1] - 1

    def next(self) -> tuple[int, int]:
        self._r += 1
        nr, nc = self.shape
        if self._r >= nr:
            self._r = 0
            self._c += 1
            if self._c >= nc:
                self.go_to_first()
                self._r += 1
        return self._r, self._c

    def prev(self) -> tuple[int, int]:
        self._r -= 1
        if self._r < 0:
            nr, nc = self.shape
            self._r = nr - 1
            self._c -= 1
            if self._c < 0:
                self.go_to_last()
                self._r -= 1
        return self._r, self._c
