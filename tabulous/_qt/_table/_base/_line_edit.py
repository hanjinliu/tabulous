from __future__ import annotations

import re
import ast
from typing import TYPE_CHECKING, Callable, cast
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
import pandas as pd

from ..._qt_const import MonospaceFontFamily
from ..._keymap import QtKeys
from ....types import HeaderInfo
from ...._selection_model import Index

if TYPE_CHECKING:
    from qtpy.QtCore import pyqtBoundSignal
    import pandas as pd
    from ._table_base import QMutableTable
    from ._enhanced_table import _QTableViewEnhanced
    from ._header_view import QDataFrameHeaderView


class _QTableLineEdit(QtW.QLineEdit):
    """LineEdit widget with dtype checker and custom defocusing."""

    _VALID = QtGui.QColor(186, 222, 244, 200)
    _INVALID = QtGui.QColor(255, 0, 0, 200)
    _EVAL_PREFIX = "="
    _REF_PREFIX = "&="

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

    def _is_text_valid(self) -> bool:
        """True if text is valid for this cell."""
        raise NotImplementedError()

    def _pre_validation(self, text: str):
        pass

    def _on_text_changed(self, text: str) -> None:
        """Change text color to red if invalid."""
        if self.isVisible():
            self._pre_validation(text)
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


class QCellLineEdit(_QTableLineEdit):
    """Line edit used for editing cell text."""

    def _is_text_valid(self) -> bool:
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

    def _pre_validation(self, text: str):
        if text.startswith(self._EVAL_PREFIX) or text.startswith(self._REF_PREFIX):
            pos = self.cursorPosition()
            self.setText("")
            line = self.parentTableView()._create_eval_editor(*self._pos, text)
            line.setCursorPosition(pos)


class QCellLiteralEdit(_QTableLineEdit):
    """Line edit used for evaluating cell text."""

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
        self.setPlaceholderText("Enter to eval")

        font = QtGui.QFont(MonospaceFontFamily, self.font().pointSize())
        font.setBold(True)
        self.setFont(font)

        self._initial_rect = self.rect()
        self.textChanged.connect(self._reshape_widget)

    @classmethod
    def from_table(
        self,
        qtable: _QTableViewEnhanced,
        text: str,
    ) -> QCellLiteralEdit:
        """Create a new literal editor from a table."""
        parent = qtable.viewport()
        table = qtable.parentTable()
        rect = qtable.visualRect(
            qtable.model().index(*qtable._selection_model.current_index)
        )
        line = QCellLiteralEdit(parent, table, qtable._selection_model.current_index)
        geometry = line.geometry()
        geometry.setWidth(rect.width())
        geometry.setHeight(rect.height())
        geometry.moveCenter(rect.center())
        line.setGeometry(geometry)
        line.setText(text)
        line.setFocus()
        line.selectAll()
        return line

    def eval_and_close(self):
        """
        Evaluate the text, update the table and close editor.

        This function strictly check out put shape to determine how to assign array results
        to the table.
        """
        raw_text = self.text()
        if raw_text.startswith(self._EVAL_PREFIX):
            text = raw_text.lstrip(self._EVAL_PREFIX).strip()
            self.eval_text(text)
        elif raw_text.startswith(self._REF_PREFIX):
            from ...._graph import Graph

            text = raw_text.lstrip(self._REF_PREFIX).strip()
            selections = self.extract_selections(text)
            evaluator = self._get_evaluator(text, update_index=False)
            # search the parent QBaseTable
            # FIXME: this is a hack, we should find a better way to do this
            viewer = self._table.parentViewer()._table_viewer
            for table in viewer.tables:
                if table.native is self._table:
                    graph = Graph(table, evaluator, selections)
                    break
            else:
                raise ValueError("Cannot find table in viewer")
            graph.connect()
            self._table._qtable_view._ref_graphs[Index(*self._pos)] = graph
        else:
            raise RuntimeError(f"Invalid text {raw_text!r}")
        self.close_editor()
        return None

    def _get_evaluator(self, text: str, update_index: bool = True) -> LiteralCallable:
        import numpy as np
        import pandas as pd

        qtable = self.parentTableView()
        table = qtable.parentTable()
        qviewer = qtable.parentViewer()

        def evaluator():
            try:
                df = table.dataShown(parse=True)
                ns = qviewer._namespace.value()
                ns.update(df=df)
                out = eval(text, ns, {})

                _row, _col = self._pos

                if isinstance(out, pd.DataFrame):
                    if out.shape[0] > 1 and out.shape[1] == 1:  # 1D array
                        out = out.iloc[:, 0]
                        _row, _col = _infer_slices(df, out, _row, _col)
                    elif out.size == 1:
                        out = out.iloc[0, 0]
                    else:
                        raise NotImplementedError("Cannot assign a DataFrame now.")

                elif isinstance(out, pd.Series):
                    if out.shape == (1,):  # scalar
                        out = out[0]
                    else:  # update a column
                        _row, _col = _infer_slices(df, out, _row, _col)

                elif isinstance(out, np.ndarray):
                    if out.ndim > 2:
                        raise ValueError("Cannot assign a >3D array.")
                    out = np.squeeze(out)
                    if out.ndim == 0:  # scalar
                        out = table.convertValue(_row, _col, out.item())
                    elif out.ndim == 1:  # 1D array
                        _row = slice(_row, _row + out.shape[0])
                        _col = slice(_col, _col + 1)
                    else:
                        _row = slice(_row, _row + out.shape[0])
                        _col = slice(_col, _col + out.shape[1])

                else:
                    out = table.convertValue(_row, _col, out)

            except Exception as e:
                if not isinstance(e, (SyntaxError, AttributeError)):
                    # These might be caused by mistouching. Don't close the editor.
                    self.close_editor()
                raise e

            if isinstance(_row, slice) and isinstance(_col, slice):  # set 1D array
                out = pd.DataFrame(out).astype(str)
                if _row.start == _row.stop - 1:  # row vector
                    out = out.T
                with qtable._selection_model.blocked():
                    table.setDataFrameValue(_row, _col, out)
                if update_index:
                    qtable._selection_model.move_to(_row.stop - 1, _col.stop - 1)

            elif isinstance(_row, int) and isinstance(_col, int):  # set scalar
                with qtable._selection_model.blocked():
                    table.setDataFrameValue(_row, _col, str(out))
                if update_index:
                    qtable._selection_model.move_to(_row, _col)

            else:
                raise RuntimeError(_row, _col)  # Unreachable
            return None

        return LiteralCallable(text, evaluator)

    def eval_text(self, text: str) -> None:
        if text == "":
            return
        return self._get_evaluator(text)()

    def close_editor(self):
        """Close this editor and deal with all the descruction."""
        qtable = self.parentTableView()
        qtable._selection_model.moved.disconnect(self._on_selection_changed)
        self.hide()
        del qtable._focused_widget
        self.deleteLater()
        qtable.setFocus()
        return None

    def extract_selections(self, text: str) -> list[tuple[slice, slice]]:
        qtable_view = self.parentTableView()
        df = qtable_view.model().df

        selections: list[tuple[slice, slice]] = []
        for expr in _find_all_dataframe_expr(text):
            if expr.startswith("df["):
                # df['val'][...]
                colname, rsl_str = expr[3:-1].split("][")
                c_start = df.columns.get_loc(eval(colname))
                rsl = _parse_slice(rsl_str)
                csl = slice(c_start, c_start + 1)
            else:
                # df.loc[...]
                rsl_str, csl_str = expr[7:-1].split(", ")
                rsl = _parse_slice_loc(rsl_str, df.index)
                csl = _parse_slice_loc(csl_str, df.columns)
            selections.append((rsl, csl))
        return selections

    def _is_text_valid(self) -> bool:
        """Try to parse the text and return True if it is valid."""
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

    def _pre_validation(self, text: str):
        if not (
            text.startswith(self._EVAL_PREFIX) or text.startswith(self._REF_PREFIX)
        ):
            self.close_editor()
            qtable = self.parentTableView()
            index = qtable.model().index(*self._pos)
            qtable.edit(index)
            line = QtW.QApplication.focusWidget()
            if not isinstance(line, QtW.QLineEdit):
                return None
            line = cast(QtW.QLineEdit, line)
            line.setText(text)
            line.setCursorPosition(self.cursorPosition())
            return

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        keys = QtKeys(a0)
        qtable = self.parentTableView()
        if keys.is_moving():
            pos = self.cursorPosition()
            nchar = len(self.text())
            rng = qtable._selection_model.ranges[-1]
            not_same_cell = not (
                rng[0].start == rng[0].stop - 1
                and rng[1].start == rng[1].stop - 1
                and self._pos == (rng[0].start, rng[1].start)
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
        if keys.is_typing() or keys in ("Backspace", "Delete"):
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
            if rsl.start == rsl.stop - 1:
                sl1 = rsl.start
            else:
                sl1 = f"{rsl.start}:{rsl.stop}"
            to_be_added = f"df[{columns[csl.start]!r}][{sl1}]"
        else:
            index = _df.index
            if rsl.start == rsl.stop - 1:
                sl1 = index[rsl.start]
            else:
                sl1 = f"{index[rsl.start]!r}:{index[rsl.stop-1]!r}"
            sl0 = f"{columns[csl.start]!r}:{columns[csl.stop-1]!r}"
            to_be_added = f"df.loc[{sl1}, {sl0}]"

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


class LiteralCallable:
    def __init__(self, expr: str, func: Callable):
        self._expr = expr
        self._func = func

    def __call__(self, *args, **kwargs):
        return self._func(*args, *kwargs)

    @property
    def expr(self) -> str:
        return self._expr


_PATTERN_DF = re.compile(r"df\[.+?\]\[.+?\]")
_PATTERN_LOC = re.compile(r"df\.loc\[.+?\]")
_PATTERN_EITHER = re.compile(r"df\[.+?\]\[.+?\]|df\.loc\[.+?\]")


def _find_last_dataframe_expr(s: str) -> int:
    """
    Detect last `df[...][...]` expression from given string.

    Returns start index if matched, otherwise -1.
    """
    start = s.rfind("df[")
    if start == -1:
        start = s.rfind("df.loc[")
        if start == -1:
            return -1
        else:
            ptn = _PATTERN_LOC
    else:
        ptn = _PATTERN_DF
    if _match := ptn.match(s[start:]):
        return _match.start() + start
    return -1


def _find_all_dataframe_expr(s: str) -> list[str]:
    return _PATTERN_EITHER.findall(s)


def _parse_slice(s: str) -> slice:
    if ":" in s:
        start_str, stop_str = s.split(":")
        start = eval(start_str)
        stop = eval(stop_str)
    else:
        start = eval(s)
        stop = start + 1
    return slice(start, stop)


def _parse_slice_loc(s: str, index: pd.Index) -> slice:
    if ":" in s:
        start_str, stop_str = s.split(":")
        start = index.get_loc(eval(start_str))
        stop = index.get_loc(eval(stop_str)) + 1
    else:
        start = index.get_loc(eval(s))
        stop = start + 1
    return slice(start, stop)


def _infer_slices(
    df: pd.DataFrame,
    out: pd.Series,
    r: int,
    c: int,
) -> tuple[slice, slice]:
    """Infer how to concatenate ``out`` to ``df``."""

    #      x | x | x |
    #      x |(1)| x |(2)
    #      x | x | x |
    #     ---+---+---+---
    #        |(3)|   |(4)

    # 1. Return as a column vector for now.
    # 2. Return as a column vector.
    # 3. Return as a row vector.
    # 4. Cannot determine in which orientation results should be aligned. Raise Error.

    _nr, _nc = df.shape
    if _nc <= c:  # case 2, 4
        _orientation = "c"
    elif _nr <= r:  # case 3
        _orientation = "r"
    else:  # case 1
        _orientation = "infer"

    if _orientation == "infer":
        try:
            df.loc[:, out.index]
        except KeyError:
            try:
                df.loc[out.index, :]
            except KeyError:
                raise KeyError("Could not infer output orientation.")
            else:
                _orientation = "c"
        else:
            _orientation = "r"

    if _orientation == "r":
        rloc = slice(r, r + 1)
        istart = df.columns.get_loc(out.index[0])
        istop = df.columns.get_loc(out.index[-1]) + 1
        if (df.columns[istart:istop] == out.index).all():
            cloc = slice(istart, istop)
        else:
            raise ValueError("Output Series is not well sorted.")
    elif _orientation == "c":
        istart = df.index.get_loc(out.index[0])
        istop = df.index.get_loc(out.index[-1]) + 1
        if (df.index[istart:istop] == out.index).all():
            rloc = slice(istart, istop)
        else:
            raise ValueError("Output Series is not well sorted.")
        cloc = slice(c, c + 1)
    else:
        raise RuntimeError(_orientation)  # unreachable

    # check (r, c) is in the range
    if not (rloc.start <= r < rloc.stop and cloc.start <= c < cloc.stop):
        raise ValueError(
            f"The cell on editing {(r, c)} is not in the range of output "
            f"({rloc.start}:{rloc.stop}, {cloc.start}:{cloc.stop})."
        )
    return rloc, cloc
