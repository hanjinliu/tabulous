from __future__ import annotations
from enum import Enum, auto

import re
import ast
from typing import TYPE_CHECKING, cast
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
import pandas as pd

from tabulous._qt._qt_const import MonospaceFontFamily
from tabulous._qt._keymap import QtKeys
from tabulous.types import HeaderInfo, EvalInfo
from tabulous._utils import get_config
from tabulous._selection_op import (
    find_last_dataframe_expr,
    construct,
)

if TYPE_CHECKING:
    from types import ModuleType
    from qtpy.QtCore import pyqtBoundSignal
    import pandas as pd
    from ._table_base import QMutableTable
    from ._enhanced_table import _QTableViewEnhanced
    from ._header_view import QDataFrameHeaderView

_CONFIG = get_config()
_LEFT_LIKE = frozenset(
    {"Left", "Ctrl+Left", "Shift+Left", "Ctrl+Shift+Left", "Home", "Shift+Home"}
)
_RIGHT_LIKE = frozenset(
    {"Right", "Ctrl+Right", "Shift+Right", "Ctrl+Shift+Right", "End", "Shift+End"}
)


class _QTableLineEdit(QtW.QLineEdit):
    """LineEdit widget with dtype checker and custom defocusing."""

    _VALID = QtGui.QColor(186, 222, 244, 200)
    _INVALID = QtGui.QColor(255, 0, 0, 200)
    _EVAL_PREFIX = _CONFIG.cell.eval_prefix
    _REF_PREFIX = _CONFIG.cell.ref_prefix

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
        """The current exception that happened in the cell."""
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

    @classmethod
    def _is_eval_like(cls, text: str) -> bool:
        return text.startswith(cls._EVAL_PREFIX) or text.startswith(cls._REF_PREFIX)

    def parentTableView(self) -> _QTableViewEnhanced:
        return self.parent().parent()

    def _is_text_valid(self) -> bool:
        """True if text is valid for this cell."""
        raise NotImplementedError()

    def _on_text_changed(self, text: str) -> None:
        """Change text color to red if invalid."""
        palette = QtGui.QPalette()
        self._is_valid = self._is_text_valid()
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

        elif keys == "F2":  # editing fails
            return None
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
            if not self._is_text_valid():
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

    def _is_text_valid(self) -> bool:
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


class _EventFilter(QtCore.QObject):
    """An event filter for text completion by tab."""

    def eventFilter(self, o: QCellLiteralEdit, e: QtCore.QEvent):
        if e.type() == QtCore.QEvent.Type.KeyPress:
            e = cast(QtGui.QKeyEvent, e)
            if e.key() == Qt.Key.Key_Tab:
                o._on_tab_clicked()
                return True
        return False


class QCellLiteralEdit(_QTableLineEdit):
    """Line edit used for evaluating cell text."""

    class Mode(Enum):
        """Editing mode of the cell line edit."""

        TEXT = auto()
        EVAL = auto()

    def __init__(
        self,
        parent: QtCore.QObject | None = None,
        table: QMutableTable | None = None,
        pos: tuple[int, int] = (0, 0),
    ):
        super().__init__(parent, table, pos)
        qtable = self.parentTableView()
        qtable._selection_model.moved.connect(self._on_selection_changed)
        qtable._focused_widget = self

        self._initial_rect = self.rect()
        self._self_focused = True
        self._completion_module: ModuleType | None = None

        self._event_filter = _EventFilter(self)
        self.installEventFilter(self._event_filter)

        self.mode = self.Mode.TEXT
        self.textEdited.connect(self._ensure_visible)

    @classmethod
    def from_table(
        cls,
        qtable: _QTableViewEnhanced,
        text: str,
    ) -> QCellLiteralEdit:
        """Create a new literal editor from a table."""
        parent = qtable.viewport()
        table = qtable.parentTable()
        rect = qtable.visualRect(
            qtable.model().index(*qtable._selection_model.current_index)
        )
        line = cls(parent, table, qtable._selection_model.current_index)
        line.setMinimumSize(1, 1)
        geometry = line.geometry()
        geometry.setWidth(rect.width())
        geometry.setHeight(rect.height())
        geometry.moveCenter(rect.center())
        line.setGeometry(geometry)
        line.setText(text)

        if cls._is_eval_like(text):
            line.mode = cls.Mode.EVAL

        line.setFocus()
        line.selectAll()
        return line

    @classmethod
    def _parse_ref(cls, raw_text: str) -> tuple[str, bool]:
        """Convert texts if it starts with the evaluation prefixes."""
        if raw_text.startswith(cls._REF_PREFIX):
            text = raw_text.lstrip(cls._REF_PREFIX).strip()
            is_ref = True
        elif raw_text.startswith(cls._EVAL_PREFIX):
            text = raw_text.lstrip(cls._EVAL_PREFIX).strip()
            is_ref = False
        else:
            raise RuntimeError("Unreachable")
        return text, is_ref

    @property
    def mode(self) -> Mode:
        """Edit mode."""
        return self._mode

    @mode.setter
    def mode(self, val: Mode) -> None:
        """Set edit mode."""
        self._mode = self.Mode(val)
        if self._mode is self.Mode.EVAL:
            font = QtGui.QFont(MonospaceFontFamily, self.font().pointSize())
            font.setBold(True)
            self.setFont(font)
        else:
            font = QtGui.QFont(_CONFIG.table.font, self.font().pointSize())
            font.setBold(False)
            self.setFont(font)
        return None

    def _on_text_changed(self, text: str) -> None:
        """Change text color to red if invalid."""
        if self._is_eval_like(text):
            self.mode = self.Mode.EVAL
        else:
            self.mode = self.Mode.TEXT

        self._reshape_widget(text)
        self._manage_completion(text)

        palette = QtGui.QPalette()
        self._is_valid = self._is_text_valid()
        if self._is_valid:
            col = Qt.GlobalColor.black
        else:
            col = Qt.GlobalColor.red

        palette.setColor(QtGui.QPalette.ColorRole.Text, col)
        self.setPalette(palette)
        return None

    def close(self) -> None:
        """Close this editor and deal with all the descruction."""
        qtable = self.parentTableView()
        qtable._selection_model.moved.disconnect(self._on_selection_changed)
        super().close()
        del qtable._focused_widget
        self.deleteLater()
        qtable.setFocus()
        # Need to emit moved signal again, otherwise table paint sometimes fails.
        qtable._selection_model.move_to(*qtable._selection_model.current_index)
        return None

    def eval_and_close(self) -> None:
        """Evaluate the text and close this editor."""
        if self._mode is self.Mode.TEXT:
            self._table.setDataFrameValue(*self._pos, self.text())
            self.close()
        else:
            text, is_ref = self._parse_ref(self.text())
            row, col = self._pos
            info = EvalInfo(row=row, column=col, expr=text, is_ref=is_ref)
            self._table.evaluatedSignal.emit(info)
        return None

    def _on_tab_clicked(self) -> None:
        """Tab-clicked event."""
        if self.mode is self.Mode.TEXT:
            # move right
            qtable = self.parentTableView()
            self.eval_and_close()
            qtable._selection_model.move(0, 1)
        elif self.mode is self.Mode.EVAL:
            # clear selection (= auto completion)
            nchar = len(self.text())
            self.setSelection(nchar, nchar)
        else:
            raise RuntimeError("Unreachable")

    def _is_text_valid(self) -> bool:
        """Try to parse the text and return True if it is valid."""
        if self.mode is self.Mode.TEXT:
            r, c = self._pos
            try:
                convert_value = self._table._get_converter(c)
                convert_value(c, self.text())
            except Exception as e:
                self.current_exception = e
                return False
            else:
                self.current_exception = None
                return True
        elif self.mode is self.Mode.EVAL:
            raw_text = self.text()
            if raw_text.startswith(self._EVAL_PREFIX):
                text = raw_text.lstrip(self._EVAL_PREFIX).strip()
            elif raw_text.startswith(self._REF_PREFIX):
                text = raw_text.lstrip(self._REF_PREFIX).strip()
            else:
                return False

            if text == "":
                return True
            try:
                ast.parse(text)
            except Exception:
                return False
            return True
        else:
            raise RuntimeError("Unreachable")

    def _ensure_visible(self, text: str) -> None:
        row, col = self._pos
        qtable = self.parentTableView()
        qtable.scrollTo(qtable.model().index(row, col), qtable.ScrollHint.EnsureVisible)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        keys = QtKeys(a0)
        qtable = self.parentTableView()
        keys_str = str(keys)

        if keys.is_moving() or keys.is_moving_func():
            # cursor movements
            pos = self.cursorPosition()
            nchar = len(self.text())
            if not self._self_focused:
                # move in the parent table
                self._table._keymap.press_key(keys)
                self.setFocus()
                return None

            if keys_str in _LEFT_LIKE:
                # exit the editor if the cursor is at the beginning
                if pos == 0:
                    qtable._selection_model.move(0, -1)
                    self._self_focused = False
                    return None
                else:
                    self._self_focused = True
            elif keys_str in _RIGHT_LIKE:
                # exit the editor if the cursor is at the end
                if pos == nchar and self.selectedText() == "":
                    qtable._selection_model.move(0, 1)
                    self._self_focused = False
                    return None
                else:
                    self._self_focused = True

            else:
                self._self_focused = False

        elif keys == "Return":
            return self.eval_and_close()
        elif keys == "Esc":
            qtable._selection_model.move_to(*self._pos)
            self.close()
            return None
        elif keys == "F2":  # editing fails
            return None

        if keys.is_typing() or keys_str in ("Backspace", "Delete"):
            if keys_str in ("Backspace", "Delete"):
                self._completion_module = None
            with qtable._selection_model.blocked():
                qtable._selection_model.move_to(*self._pos)
            self._self_focused = True
        self.setFocus()
        return QtW.QLineEdit.keyPressEvent(self, a0)

    def _on_selection_changed(self) -> None:
        """Update text based on the current selection."""
        qtable = self.parentTableView()
        if self.mode is self.Mode.TEXT:
            return self.eval_and_close()

        text = self.text()
        cursor_pos = self.cursorPosition()

        # prepare text
        if len(qtable._selection_model.ranges) != 1:
            # if multiple cells are selected, don't update
            return None

        rsl, csl = qtable._selection_model.ranges[-1]
        _df = qtable.model().df
        column_selected = len(qtable._selection_model._col_selection_indices) > 0
        selop = construct(
            rsl, csl, _df, method=_CONFIG.cell.slicing, column_selected=column_selected
        )

        if selop is None:  # out of bound
            return None

        if selop.area(_df) > 1:
            to_be_added = selop.fmt("df")
        else:
            to_be_added = selop.fmt_scalar("df")

        if cursor_pos == 0:
            self.setText(to_be_added + text)
        elif text[cursor_pos - 1] != "]":
            self.setText(text[:cursor_pos] + to_be_added + text[cursor_pos:])
        else:
            idx = find_last_dataframe_expr(text[:cursor_pos])
            if idx >= 0:
                self.setText(text[:idx] + to_be_added + text[cursor_pos:])
            else:
                self.setText(text[:cursor_pos] + to_be_added + text[cursor_pos:])

        return None

    def _reshape_widget(self, text: str) -> None:
        """Resize to let all the characters visible."""
        fm = QtGui.QFontMetrics(self.font())
        width = min(fm.boundingRect(text).width() + 8, 300)
        return self.resize(max(width, self._initial_rect.width()), self.height())

    def _manage_completion(self, text: str) -> None:
        """Code completion."""
        if self.mode is self.Mode.TEXT:
            return None

        if text.endswith("."):
            mod_str = _find_last_module_name(text[:-1])
            mod = self._table.parentViewer()._namespace.get(mod_str, None)
            if mod is None:
                self._completion_module = None
                return None
            self._completion_module = mod
            return None

        elif self._completion_module is None:
            return None

        idx = text.rfind(".")
        if idx < 0:
            return None
        seed = text[idx + 1 :]
        for attr in self._completion_module.__dict__.keys():
            if attr.startswith(seed):
                current_text = self.text()
                current_pos = self.cursorPosition()
                new_text = current_text[: -len(seed)] + attr
                self.blockSignals(True)
                try:
                    self.setText(new_text)
                    self.setCursorPosition(current_pos)
                    self.setSelection(current_pos, len(new_text))
                finally:
                    self.blockSignals(False)
                break
        return None


_PATTERN_IDENTIFIERS = re.compile(r"[\w\d_]+")


def _find_last_module_name(s: str):
    return _PATTERN_IDENTIFIERS.findall(s)[-1]


class QCellLabelEdit(QtW.QLineEdit):
    """A QLineEdit that can be used to edit the label of a cell."""

    def __init__(
        self,
        parent: QtCore.QObject | None = None,
        table: QMutableTable | None = None,
        pos: tuple[int, int] = (0, 0),
    ):
        super().__init__(parent)
        self._table = table
        self._pos = pos
        table_config = get_config().table
        font = QtGui.QFont(table_config.font, table_config.font_size)
        font.setBold(True)
        self.setFont(font)
        self.editingFinished.connect(self._on_editing_finished)

    def _on_editing_finished(self):
        self.editingFinished.disconnect()
        self._hide_and_delete()
        text = self.text()
        if text == "":
            text = None
        self._table.setItemLabel(*self._pos, text)
        return None

    def _hide_and_delete(self):
        self.hide()
        self.deleteLater()
        self._table._qtable_view.setFocus()
        return None

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        keys = QtKeys(event)
        pos = self.cursorPosition()
        nchar = len(self.text())
        r, c = self._pos
        if keys == "Escape":
            self._hide_and_delete()
            return None
        if keys.is_moving():
            if pos == 0 and keys == "Left" and c >= 0:
                self._on_editing_finished()
                self._table._qtable_view._selection_model.move_to(r, c - 1)
                return
            elif (
                pos == nchar
                and keys == "Right"
                and c < self._table.model().columnCount() - 1
                and self.selectedText() == ""
            ):
                self._on_editing_finished()
                self._table._qtable_view._selection_model.move_to(r, c + 1)
                return
            elif keys == "Up" and r >= 0:
                self._on_editing_finished()
                self._table._qtable_view._selection_model.move_to(r - 1, c)
                return
            elif keys == "Down" and r < self._table.model().rowCount() - 1:
                self._on_editing_finished()
                self._table._qtable_view._selection_model.move_to(r + 1, c)
                return

        elif keys == "F2":
            return
        return super().keyPressEvent(event)

    @classmethod
    def from_table(
        cls,
        qtable: _QTableViewEnhanced,
    ) -> QCellLiteralEdit:
        """Create a new literal editor from a table."""
        parent = qtable.viewport()
        table = qtable.parentTable()
        index = qtable._selection_model.current_index
        rect = qtable.visualRect(qtable.model().index(*index))
        line = cls(parent, table, index)
        line.setMinimumSize(1, 1)
        geometry = line.geometry()
        geometry.setWidth(rect.width())
        geometry.setHeight(rect.height())
        geometry.moveCenter(rect.center())
        line.setGeometry(geometry)

        text = table.itemLabel(*index)
        line.setText(text)

        line.setFocus()
        line.selectAll()
        return line
