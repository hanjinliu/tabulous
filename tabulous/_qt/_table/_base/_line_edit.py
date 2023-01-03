from __future__ import annotations
from enum import Enum, auto

import re
import ast
import sys
from typing import TYPE_CHECKING, cast
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt

from tabulous._qt._qt_const import MonospaceFontFamily
from tabulous._keymap import QtKeys
from tabulous.types import HeaderInfo, EvalInfo
from tabulous._range import RectRange, MultiRectRange
from tabulous._utils import get_config
from tabulous._selection_op import (
    find_last_dataframe_expr,
    construct,
    iter_extract,
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

MAC = sys.platform == "darwin"


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
        self._attached_tooltip = ""
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
            # html colored text
            exc_type = type(value).__name__
            text = str(value).replace("<", "&lt;").replace(">", "&gt;")
            value = f"<b><font color='red'>{exc_type}</font></b>: {text}"
        self._current_exception = str(value)
        return self.setToolTip(self._current_exception)

    @classmethod
    def _is_eval_like(cls, text: str) -> bool:
        return text.startswith(cls._EVAL_PREFIX) or text.startswith(cls._REF_PREFIX)

    def parentTableView(self) -> _QTableViewEnhanced:
        """The parent table view."""
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

    def attachToolTip(self, text: str) -> None:
        """Attach a tooltip to the widget."""
        if text:
            point = self.mapToGlobal(self.rect().bottomLeft())
            point.setX(point.x() - 2)
            point.setY(point.y() - 10)
            QtW.QToolTip.setFont(QtGui.QFont("Arial", 10))
            QtW.QToolTip.showText(point, text, self)

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

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.editingFinished.disconnect()
            self.hide()
            self.deleteLater()
            self._table._qtable_view.setFocus()
            return None
        return super().keyPressEvent(event)

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
        self._old_range: RectRange | None = None
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
        cr, cc = qtable._selection_model.current_index
        # cr = table._proxy.get_source_index(cr)
        line = cls(parent, table, (cr, cc))
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
        err_tip = ""
        if self._is_eval_like(text):
            self.mode = self.Mode.EVAL
        else:
            self.mode = self.Mode.TEXT

        self._reshape_widget(text)
        self._manage_completion(text)

        palette = QtGui.QPalette()
        self._is_valid = self._is_text_valid()
        if self._is_valid and err_tip == "":
            col = Qt.GlobalColor.black
        else:
            col = Qt.GlobalColor.red

        palette.setColor(QtGui.QPalette.ColorRole.Text, col)
        self.setPalette(palette)

        if self.mode is self.Mode.TEXT:
            self.attachToolTip("")
            return None

        # draw ranges
        _table = self._table
        ranges: list[tuple[slice, slice]] = []
        for op in iter_extract(text):
            ranges.append(op.as_iloc_slices(_table.model().df))

        if ranges:
            new_range = MultiRectRange.from_slices(ranges)
        else:
            new_range = None
        if self._old_range or new_range:
            _table._qtable_view._current_drawing_slot_ranges = new_range
            _table._qtable_view._update_all()
        self.attachToolTip(err_tip)
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
            except Exception as e:
                self.current_exception = e
                return False
            else:
                self.current_exception = None
            return True
        else:
            raise RuntimeError("Unreachable")

    def _ensure_visible(self, text: str) -> None:
        row, col = self._pos
        qtable = self.parentTableView()
        qtable.scrollTo(qtable.model().index(row, col), qtable.ScrollHint.EnsureVisible)

    def _on_selection_changed(self) -> None:
        """Update text based on the current selection."""
        qtable_view = self.parentTableView()
        if self.mode is self.Mode.TEXT:
            return self.eval_and_close()

        text = self.text()
        cursor_pos = self.cursorPosition()

        # prepare text
        if len(qtable_view._selection_model.ranges) != 1 or cursor_pos == 0:
            # If multiple cells are selected, don't update because selection range
            # is not well-defined. If cursor position is at the beginning, don't
            # update because it is before "=".
            return None

        qtable = cast("QMutableTable", qtable_view.parentTable())
        _df_filt = qtable_view.model().df
        _df_ori = qtable._data_raw
        rsl, csl = qtable_view._selection_model.ranges[-1]
        if not qtable._proxy.is_ordered and not _is_size_one(rsl):
            self.attachToolTip(
                "Table proxy is not ordered.\nCannot create cell "
                "references from table selection."
            )
            return None
        if rsl.stop is not None and rsl.stop > _df_filt.shape[0]:
            rsl = slice(rsl.start, _df_filt.shape[0])
        rsl = qtable._proxy.get_source_slice(rsl)
        table_range = RectRange.from_shape(_df_filt.shape)

        # out of border
        if not table_range.overlaps_with(RectRange(rsl, csl)):
            return None

        column_selected = len(qtable_view._selection_model._col_selection_indices) > 0
        selop = construct(
            rsl, csl, _df_ori, method="iloc", column_selected=column_selected
        )

        if selop is None:  # out of bound
            return None

        # get string that represents the selection
        if selop.area(_df_ori) > 1:
            to_be_added = selop.fmt("df")
        else:
            to_be_added = selop.resolve_indices(_df_ori, (1, 1)).fmt_scalar("df")

        # add the representation to the text at the proper position
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
            if _viewer := self._table.parentViewer():
                mod = _viewer._namespace.get(mod_str, None)
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

    def _key_press_event(self, event: QtGui.QKeyEvent) -> None:
        keys = QtKeys(event)
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
                return True

            if keys_str in _LEFT_LIKE:
                # exit the editor if the cursor is at the beginning
                if pos == 0:
                    qtable._selection_model.move(0, -1)
                    self._self_focused = False
                    self.setFocus()
                    return True
                else:
                    self._self_focused = True
                    self.setFocus()
            elif keys_str in _RIGHT_LIKE:
                # exit the editor if the cursor is at the end
                if pos == nchar and self.selectedText() == "":
                    qtable._selection_model.move(0, 1)
                    self._self_focused = False
                    self.setFocus()
                    return True
                else:
                    self._self_focused = True
                    self.setFocus()

            else:
                self._self_focused = False

        elif keys == "Return":
            self.eval_and_close()
            return True
        elif keys == "Esc":
            qtable._selection_model.move_to(*self._pos)
            self.close()
            return True
        elif keys == "F2":  # editing fails
            return True
        elif keys == "F3":
            self.eval_and_close()
            editor = QCellLabelEdit.from_table(qtable)
            editor.show()
            return True

        if keys.is_typing() or keys_str in ("Backspace", "Delete"):
            if keys_str in ("Backspace", "Delete"):
                self._completion_module = None
            with qtable._selection_model.blocked():
                qtable._selection_model.move_to(*self._pos)
            self._self_focused = True
        self.setFocus()
        return False

    if MAC:

        def event(self, a0: QtCore.QEvent) -> bool:
            # NOTE: On MacOS, up/down causes text cursor to move to the beginning/end.
            _type = a0.type()
            if _type != QtCore.QEvent.Type.KeyPress:
                return super().event(a0)
            event = QtGui.QKeyEvent(a0)
            if not self._key_press_event(event):
                super().event(a0)
            self.setFocus()
            return True

    else:

        def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
            if not self._key_press_event(event):
                return QtW.QLineEdit.keyPressEvent(self, event)


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
        self.setStyleSheet("QCellLabelEdit{ color: gray; }")
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
            return None
        elif keys == "F3":
            return None  # do nothing
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


def _is_size_one(sl: slice) -> bool:
    if sl.start is None or sl.stop is None:
        return False
    return sl.start == sl.stop - 1
