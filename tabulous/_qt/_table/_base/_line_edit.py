from __future__ import annotations

import re
import ast
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
import pandas as pd

from ..._keymap import QtKeys
from ....types import HeaderInfo

if TYPE_CHECKING:
    from qtpy.QtCore import pyqtBoundSignal
    from ._table_base import QMutableTable
    from ._enhanced_table import _QTableViewEnhanced
    from ._header_view import QDataFrameHeaderView


class _QTableLineEdit(QtW.QLineEdit):
    """LineEdit widget with dtype checker and custom defocusing."""

    _VALID = QtGui.QColor(186, 222, 244, 200)
    _INVALID = QtGui.QColor(255, 0, 0, 200)

    def __init__(
        self,
        parent: QtCore.QObject | None = None,
        table: QMutableTable | None = None,
        pos: tuple[int, int] = (0, 0),
    ):
        super().__init__(parent)
        self._table = table
        self._pos = pos
        self._is_valid = True
        self._current_exception = ""
        self.textChanged.connect(self._on_text_changed)

    @property
    def current_exception(self) -> str:
        return self._current_exception

    @current_exception.setter
    def current_exception(self, value: str | Exception | None) -> None:
        if value is None:
            value = ""
        elif isinstance(value, Exception):
            exc_type = type(value).__name__
            value = f"{exc_type}: {value}"
        self._current_exception = str(value)
        return self.setToolTip(self._current_exception)

    def parentTableView(self) -> _QTableViewEnhanced:
        return self.parent().parent()

    def isTextValid(self) -> bool:
        """True if text is valid for this cell."""
        raise NotImplementedError()

    def _on_text_changed(self, text: str) -> None:
        """Change text color to red if invalid."""
        palette = QtGui.QPalette()
        self._is_valid = self.isTextValid()
        if self._is_valid:
            col = Qt.GlobalColor.black
        else:
            col = Qt.GlobalColor.red

        palette.setColor(QtGui.QPalette.ColorRole.Text, col)
        self.setPalette(palette)
        return None

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle key press events."""
        keys = QtKeys(event)
        pos = self.cursorPosition()
        nchar = len(self.text())
        r, c = self._pos
        if keys.is_moving():
            if pos == 0 and keys == "Left" and c >= 0:
                self.parentTableView().setFocus()
                self._table._qtable_view._selection_model.move_to(r, c - 1)
                return
            elif (
                pos == nchar
                and keys == "Right"
                and c < self._table.model().columnCount() - 1
                and self.selectedText() == ""
            ):
                self.parentTableView().setFocus()
                self._table._qtable_view._selection_model.move_to(r, c + 1)
                return
            elif keys == "Up" and r >= 0:
                self.parentTableView().setFocus()
                self._table._qtable_view._selection_model.move_to(r - 1, c)
                return
            elif keys == "Down" and r < self._table.model().rowCount() - 1:
                self.parentTableView().setFocus()
                self._table._qtable_view._selection_model.move_to(r + 1, c)
                return

        return super().keyPressEvent(event)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        super().paintEvent(a0)
        rect = self.rect()
        p0 = rect.bottomLeft()
        p1 = rect.bottomRight()
        painter = QtGui.QPainter(self)
        if self._is_valid:
            painter.setPen(QtGui.QPen(self._VALID, 3))
        else:
            painter.setPen(QtGui.QPen(self._INVALID, 3))
        painter.drawLine(p0, p1)
        painter.end()
        return None


class _QHeaderLineEdit(_QTableLineEdit):
    """Line edit used for editing header text."""

    ALIGNMENT: Qt.AlignmentFlag

    def _get_index(self) -> int:
        raise NotImplementedError()

    def _get_rect(self, index: int) -> QtCore.QRect:
        raise NotImplementedError()

    def _get_pandas_axis(self) -> pd.Index:
        raise NotImplementedError()

    def _get_signal(self) -> pyqtBoundSignal:
        raise NotImplementedError()

    def __init__(
        self,
        parent: QDataFrameHeaderView,
        table: QMutableTable | None = None,
        pos: tuple[int, int] = (0, 0),
    ):
        super().__init__(parent, table, pos)

        index = self._get_index()
        geometry = self._get_rect(index)
        geometry.adjust(2, 1, -2, -1)
        self.setGeometry(geometry)
        self.setAlignment(self.ALIGNMENT)
        self.setHidden(False)

        df_axis = self._get_pandas_axis()
        if index < df_axis.size:
            old_value = df_axis[index]
            text = str(old_value)
        else:
            # spreadsheet
            old_value = None
            text = ""

        @self.editingFinished.connect
        def _set_header_data():
            self.editingFinished.disconnect()
            value = self.text()
            err = None
            if not self.isTextValid():
                err = ValueError(f"Duplicated name {value!r}")
            elif value != text and value:
                self._get_signal().emit(HeaderInfo(index, value, text))
            table = self._table._qtable_view
            table.setFocus()
            self.deleteLater()
            if err:
                raise err
            return None

        self.setText(text)
        self.selectAll()
        self.setFocus()

    def isTextValid(self) -> bool:
        """True if text is valid for this cell."""
        text = self.text()
        pd_index = self._get_pandas_axis()
        idx = self._get_index()
        not_in = text not in pd_index
        if idx < pd_index.size:
            valid = text == pd_index[idx] or not_in
        else:
            valid = not_in

        if valid:
            self.current_exception = None
        else:
            self.current_exception = ValueError(f"Duplicated name {text!r}")
        return valid


class QVerticalHeaderLineEdit(_QHeaderLineEdit):
    """Line edit used for vertical editing header text."""

    ALIGNMENT = Qt.AlignmentFlag.AlignLeft

    def _get_index(self) -> int:
        return self._pos[0]

    def _get_rect(self, index: int) -> QtCore.QRect:
        header = self._table._qtable_view.verticalHeader()
        width = header.width()
        height = header.sectionSize(index)
        left = header.rect().left()
        top = header.sectionViewportPosition(index)
        return QtCore.QRect(left, top, width, height)

    def _get_pandas_axis(self) -> pd.Index:
        return self._table.model().df.index

    def _get_signal(self):
        return self._table.rowChangedSignal


class QHorizontalHeaderLineEdit(_QHeaderLineEdit):
    """Line edit used for horizontal editing header text."""

    ALIGNMENT = Qt.AlignmentFlag.AlignCenter

    def _get_index(self) -> int:
        return self._pos[1]

    def _get_rect(self, index: int) -> QtCore.QRect:
        header = self._table._qtable_view.horizontalHeader()
        width = header.sectionSize(index)
        height = header.height()
        left = header.sectionViewportPosition(index)
        top = header.rect().top()
        return QtCore.QRect(left, top, width, height)

    def _get_pandas_axis(self) -> pd.Index:
        return self._table.model().df.columns

    def _get_signal(self):
        return self._table.columnChangedSignal


class QCellLineEdit(_QTableLineEdit):
    """Line edit used for editing cell text."""

    def isTextValid(self) -> bool:
        """True if text is valid for this cell."""
        r, c = self._pos
        try:
            convert_value = self._table._get_converter(c)
            convert_value(r, c, self.text())
        except Exception as e:
            self.current_exception = e
            return False
        else:
            self.current_exception = None
            return True


class QCellLiteralEdit(_QTableLineEdit):
    def __init__(
        self,
        parent: QtCore.QObject | None = None,
        table: QMutableTable | None = None,
        pos: tuple[int, int] = (0, 0),
    ):
        import weakref

        super().__init__(parent, table, pos)
        qtable = self.parentTableView()
        qtable._selection_model.moved.connect(self._on_selection_changed)
        qtable._overlay_editor = weakref.ref(self)
        self.setPlaceholderText("Enter to eval")

        font = QtGui.QFont("Courier New", self.font().pointSize())
        font.setBold(True)
        self.setFont(font)

        self._initial_rect = self.rect()
        self.textChanged.connect(self._reshape_widget)

    @classmethod
    def from_rect(
        self,
        rect: QtCore.QRect,
        parent: QtW.QWidget,
        text: str,
    ) -> QCellLiteralEdit:
        qtable: _QTableViewEnhanced = parent.parent()
        table = qtable.parentTable()
        line = QCellLiteralEdit(parent, table, qtable._selection_model.current_index)
        geometry = line.geometry()
        geometry.setWidth(rect.width())
        geometry.setHeight(rect.height())
        geometry.moveCenter(rect.center())
        line.setGeometry(geometry)
        line.setText(text)
        line.setHidden(False)
        line.setFocus()
        line.selectAll()
        return line

    def eval_and_close(self):
        import numpy as np
        import pandas as pd

        text = self.text().lstrip("=")
        if text == "":
            self.close_editor()

        try:
            df = self.parentTableView().parentTable().getDataFrame()
            out = eval(text, {"np": np, "pd": pd, "df": df}, {})

            _row, _col = self._pos
            qtable = self.parentTableView()
            table = qtable.parentTable()

            if isinstance(out, pd.DataFrame):
                if out.shape[0] > 1 and out.shape[1] == 1:  # 1D array
                    out = out.iloc[:, 0]
                    _row = slice(0, len(out))
                elif out.size == 1:
                    out = out.iloc[0, 0]
                else:
                    raise NotImplementedError("Cannot assign a DataFrame now.")
            elif isinstance(out, pd.Series):
                if out.shape == (1,):  # scalar
                    out = out[0]
                else:  # update a column
                    out = out
                    _row = slice(0, len(out))
            elif isinstance(out, np.ndarray):
                if out.ndim > 2:
                    raise ValueError("Cannot assign a >3D array.")
                out = np.squeeze(out)
                if out.ndim == 0:  # scalar
                    out = table.convertValue(_row, _col, out.item())
                if out.ndim == 1:  # 1D array
                    out = pd.Series(out)
                    _row = slice(0, len(out))
                else:
                    raise NotImplementedError("Cannot assign a DataFrame now.")
            else:
                out = table.convertValue(_row, _col, out)

        except Exception as e:
            if not isinstance(e, SyntaxError):
                self.close_editor()
            raise e

        if isinstance(_row, slice):  # set 1D array
            table.setDataFrameValue(
                _row, slice(_col, _col + 1), pd.DataFrame(out).astype(str)
            )
            qtable._selection_model.move_to(_row.stop - 1, _col)
        else:  # set scalar
            table.setDataFrameValue(_row, _col, str(out))
            qtable._selection_model.move_to(_row, _col)

        self.close_editor()
        return None

    def close_editor(self):
        qtable = self.parentTableView()
        qtable._selection_model.moved.disconnect(self._on_selection_changed)
        self.hide()
        qtable._overlay_editor = None
        self.deleteLater()
        qtable.setFocus()
        return None

    def isTextValid(self) -> bool:
        text = self.text().lstrip("=")
        if text == "":
            return True
        try:
            ast.parse(text)
        except Exception:
            return False
        return True

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        keys = QtKeys(a0)
        qtable = self.parentTableView()
        if keys.is_moving():
            pos = self.cursorPosition()
            nchar = len(self.text())
            rng = qtable._selection_model.ranges[-1]
            not_same_cell = not (
                self._pos == qtable._selection_model.current_index
                and rng[0].start == rng[0].stop - 1
                and rng[1].start == rng[1].stop - 1
            )
            if not_same_cell:
                # move in the parent table
                self._table._keymap.press_key(keys)
                self.setFocus()
                return None

            if keys == "Left" and pos == 0:
                qtable._selection_model.move(0, -1)
                return None
            elif keys == "Right" and pos == nchar and self.selectedText() == "":
                qtable._selection_model.move(0, 1)
                return None

        elif keys == "Return":
            return self.eval_and_close()
        elif keys == "Esc":
            qtable._selection_model.move_to(*self._pos)
            return self.close_editor()
        if keys.is_typing():
            with qtable._selection_model.blocked():
                qtable._selection_model.move_to(*self._pos)
        self.setFocus()
        return QtW.QLineEdit.keyPressEvent(self, a0)

    def _on_selection_changed(self):
        """Update text based on the current selection."""
        text = self.text()
        cursor_pos = self.cursorPosition()
        qtable = self.parentTableView()

        # prepare text
        if len(qtable._selection_model.ranges) != 1:
            # if multiple cells are selected, don't update
            return None

        rsl, csl = qtable._selection_model.ranges[-1]
        _df = qtable.model().df
        columns = _df.columns
        nr, nc = _df.shape

        if rsl.stop > nr:
            if rsl.start >= nr:
                return None
            rsl = slice(rsl.start, nr)
        if csl.stop > nc:
            if csl.start >= nc:
                return None
            csl = slice(csl.start, nc)

        if csl.start == csl.stop - 1:
            sl0 = repr(columns[csl.start])
        else:
            sl0 = f"{columns[csl.start]}:{columns[csl.stop]}"
        if rsl.start == rsl.stop - 1:
            sl1 = rsl.start
        else:
            sl1 = f"{rsl.start}:{rsl.stop}"
        to_be_added = f"df[{sl0}][{sl1}]"

        if cursor_pos == 0:
            self.setText(to_be_added + text)
        elif text[cursor_pos - 1] != "]":
            self.setText(text[:cursor_pos] + to_be_added + text[cursor_pos:])
        else:
            idx = _find_last_dataframe_expr(text[:cursor_pos])
            if idx >= 0:
                self.setText(text[:idx] + to_be_added + text[cursor_pos:])
            else:
                self.setText(text[:cursor_pos] + to_be_added + text[cursor_pos:])

        return None

    def _reshape_widget(self, text: str):
        fm = QtGui.QFontMetrics(self.font())
        width = min(fm.boundingRect(text).width() + 8, 300)
        return self.resize(max(width, self._initial_rect.width()), self.height())


_PATTERN = re.compile(r"df\[.+\]\[.+\]")


def _find_last_dataframe_expr(s: str) -> int:
    """
    Detect last `df[...][...]` expression from given string.

    Returns start index if matched, otherwise -1.
    """
    start = s.rfind("df[")
    if start == -1:
        return -1
    if _match := _PATTERN.match(s[start:]):
        return _match.start() + start
    return -1
