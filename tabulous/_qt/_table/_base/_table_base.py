from __future__ import annotations
from typing import Any, Callable, overload
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Signal, Qt

import numpy as np
import pandas as pd

from collections_undo import UndoManager
from ._model_base import AbstractDataFrameModel
from ..._utils import show_messagebox
from ....types import FilterType, ItemInfo, HeaderInfo, Selections

# Flags
_EDITABLE = (
    QtW.QAbstractItemView.EditTrigger.EditKeyPressed
    | QtW.QAbstractItemView.EditTrigger.DoubleClicked
)
_READ_ONLY = QtW.QAbstractItemView.EditTrigger.NoEditTriggers
_SCROLL_PER_PIXEL = QtW.QAbstractItemView.ScrollMode.ScrollPerPixel


class _QTableViewEnhanced(QtW.QTableView):
    selectionChangedSignal = Signal()
    rightClickedSignal = Signal(QtCore.QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_pos: QtCore.QPoint | None = None
        self._was_right_dragging: bool = False
        self._zoom = 1.0
        self._initial_font_size = self.font().pointSize()
        vheader, hheader = self.verticalHeader(), self.horizontalHeader()
        self.setFrameStyle(QtW.QFrame.Shape.Box)
        vheader.setFrameStyle(QtW.QFrame.Shape.Box)
        hheader.setFrameStyle(QtW.QFrame.Shape.Box)
        vheader.resize(16, vheader.height())
        self.setStyleSheet("QHeaderView::section { border: 1px solid black}")
        vheader.setMinimumSectionSize(0)
        hheader.setMinimumSectionSize(0)
        vheader.font().setPointSize(self._initial_font_size)
        hheader.font().setPointSize(self._initial_font_size)

        vheader.setDefaultSectionSize(28)
        hheader.setDefaultSectionSize(100)

        hheader.setSectionResizeMode(QtW.QHeaderView.ResizeMode.Fixed)
        vheader.setSectionResizeMode(QtW.QHeaderView.ResizeMode.Fixed)

        self._initial_section_size = (
            hheader.defaultSectionSize(),
            vheader.defaultSectionSize(),
        )
        self.setZoom(1.0)  # initialize

    def selectionChanged(
        self,
        selected: QtCore.QItemSelection,
        deselected: QtCore.QItemSelection,
    ) -> None:
        """Evoked when table selection range is changed."""
        self.selectionChangedSignal.emit()
        return super().selectionChanged(selected, deselected)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        """Register clicked position"""
        if e.button() == Qt.MouseButton.RightButton:
            self._last_pos = e.pos()
            self._was_right_dragging = False
        return super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        """Scroll table plane when mouse is moved with right click."""
        if self._last_pos is not None:
            pos = e.pos()
            dy = pos.y() - self._last_pos.y()
            dx = pos.x() - self._last_pos.x()
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self._last_pos = pos
            self._was_right_dragging = True
        return super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        """Delete last position."""
        if e.button() == Qt.MouseButton.RightButton and not self._was_right_dragging:
            self.rightClickedSignal.emit(e.pos())
        self._last_pos = None
        self._was_right_dragging = False
        return super().mouseReleaseEvent(e)

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        """Evoke parent keyPressEvent."""
        if (
            e.modifiers()
            in (
                Qt.KeyboardModifier.NoModifier,
                Qt.KeyboardModifier.ShiftModifier,
            )
            and (Qt.Key.Key_Exclam <= e.key() <= Qt.Key.Key_ydiaeresis)
        ):
            parent = self.parent()
            if isinstance(parent, QBaseTable):
                parent.keyPressEvent(e)
        else:
            return super().keyPressEvent(e)

    def zoom(self) -> float:
        """Get current zoom factor."""
        return self._zoom

    def setZoom(self, value: float) -> None:
        """Set zoom factor."""
        if not 0.25 <= value <= 2.0:
            raise ValueError("Zoom factor must between 0.25 and 2.0.")
        # To keep table at the same position.
        zoom_ratio = 1 / self._zoom * value
        pos = self.verticalScrollBar().sliderPosition()
        self.verticalScrollBar().setSliderPosition(int(pos * zoom_ratio))
        pos = self.horizontalScrollBar().sliderPosition()
        self.horizontalScrollBar().setSliderPosition(int(pos * zoom_ratio))

        # Zoom font size
        font = self.font()
        font.setPointSize(int(self._initial_font_size * value))
        self.setFont(font)
        self.verticalHeader().setFont(font)
        self.horizontalHeader().setFont(font)

        # Zoom section size of headers
        h, v = self._initial_section_size
        self.setSectionSize(int(h * value), int(v * value))

        # Update stuff
        self._zoom = value
        return

    def wheelEvent(self, e: QtGui.QWheelEvent) -> None:
        """Zoom in/out table."""
        if e.modifiers() & Qt.ControlModifier:
            dt = e.angleDelta().y() / 120
            zoom = self.zoom() + 0.15 * dt
            self.setZoom(min(max(zoom, 0.25), 2.0))
            return None

        return super().wheelEvent(e)

    def sectionSize(self) -> tuple[int, int]:
        return (
            self.horizontalHeader().defaultSectionSize(),
            self.verticalHeader().defaultSectionSize(),
        )

    def setSectionSize(self, horizontal: int, vertical: int) -> None:
        """Update section size of headers."""
        self.verticalHeader().setDefaultSectionSize(vertical)
        self.horizontalHeader().setDefaultSectionSize(horizontal)
        return


class QBaseTable(QtW.QWidget):
    """
    The base widget for a table.

    Abstract Methods
    ----------------
    def createQTableView(self) -> None: ...
    def getDataFrame(self) -> pd.DataFrame: ...
    def setDataFrame(self) -> None: ...
    def createModel(self) -> AbstractDataFrameModel: ...
    def tableSlice(self) -> pd.DataFrame: ...
    """

    selectionChangedSignal = Signal(list)
    _DEFAULT_EDITABLE = False

    def __init__(
        self, parent: QtW.QWidget | None = None, data: pd.DataFrame | None = None
    ):
        super().__init__(parent)
        self._filter_slice: FilterType | None = None
        self.createQTableView()
        self.createModel()
        self.setDataFrame(data)
        self._qtable_view.setVerticalScrollMode(_SCROLL_PER_PIXEL)
        self._qtable_view.setHorizontalScrollMode(_SCROLL_PER_PIXEL)
        self._qtable_view.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        delegate = TableItemDelegate(parent=self)
        self._qtable_view.setItemDelegate(delegate)
        self._qtable_view.selectionChangedSignal.connect(
            lambda: self.selectionChangedSignal.emit(self.selections())
        )
        if not self._DEFAULT_EDITABLE:
            self._qtable_view.setEditTriggers(_READ_ONLY)

    @property
    def _qtable_view(self) -> _QTableViewEnhanced:
        raise NotImplementedError()

    def createQTableView(self) -> None:
        """Create QTableView."""
        raise NotImplementedError()

    def getDataFrame(self) -> pd.DataFrame:
        raise NotImplementedError()

    def setDataFrame(self) -> None:
        raise NotImplementedError()

    def createModel(self) -> AbstractDataFrameModel:
        raise NotImplementedError()

    def tableSlice(self) -> pd.DataFrame:
        raise NotImplementedError()

    def tableShape(self) -> tuple[int, int]:
        model = self._qtable_view.model()
        nr = model.rowCount()
        nc = model.columnCount()
        return (nr, nc)

    def zoom(self) -> float:
        """Get current zoom factor."""
        return self._qtable_view.zoom()

    def setZoom(self, value: float) -> None:
        """Set zoom factor."""
        return self._qtable_view.setZoom(value)

    def itemDelegate(self) -> TableItemDelegate:
        return QtW.QTableView.itemDelegate(self._qtable_view)

    def model(self) -> AbstractDataFrameModel:
        return QtW.QTableView.model(self._qtable_view)

    def precision(self) -> int:
        """Return table value precision."""
        return self.itemDelegate().ndigits

    def setPrecision(self, ndigits: int) -> None:
        """Set table value precision."""
        ndigits = int(ndigits)
        if ndigits <= 0:
            raise ValueError("Cannot set negative precision.")
        self.itemDelegate().ndigits = ndigits

    def connectSelectionChangedSignal(self, slot):
        self.selectionChangedSignal.connect(slot)
        return slot

    def selections(self) -> Selections:
        """Get list of selections as slicable tuples"""
        qtable = self._qtable_view
        selections = qtable.selectionModel().selection()

        # selections = self.selectedRanges()
        out: Selections = []
        for i in range(len(selections)):
            sel = selections[i]
            r0 = sel.top()
            r1 = sel.bottom() + 1
            c0 = sel.left()
            c1 = sel.right() + 1
            out.append((slice(r0, r1), slice(c0, c1)))

        return out

    def setSelections(self, selections: Selections):
        """Set list of selections."""
        qtable = self._qtable_view
        qtable.clearSelection()

        model = self.model()
        nr, nc = model.df.shape
        try:
            for sel in selections:
                r, c = sel
                r0, r1, _ = r.indices(nr)
                c0, c1, _ = c.indices(nc)
                selection = QtCore.QItemSelection(
                    model.index(r0, c0), model.index(r1 - 1, c1 - 1)
                )
                qtable.selectionModel().select(
                    selection, QtCore.QItemSelectionModel.SelectionFlag.Select
                )

        except Exception as e:
            qtable.clearSelection()
            raise e

    def copyToClipboard(self, headers: bool = True):
        """Copy currently selected cells to clipboard."""
        selections = self.selections()
        if len(selections) == 0:
            return
        r_ranges = set()
        c_ranges = set()
        for rsel, csel in selections:
            r_ranges.add((rsel.start, rsel.stop))
            c_ranges.add((csel.start, csel.stop))

        nr = len(r_ranges)
        nc = len(c_ranges)
        if nr > 1 and nc > 1:
            show_messagebox(
                mode="error", title="Error", text="Wrong selection range.", parent=self
            )
            return
        else:
            data = self.model().df
            if nr == 1:
                axis = 1
            else:
                axis = 0
            ref = pd.concat([data.iloc[sel] for sel in selections], axis=axis)
            ref.to_clipboard(index=headers, header=headers)

    def readClipBoard(self) -> pd.DataFrame:
        """Read clipboard data and return as pandas DataFrame."""
        return pd.read_clipboard(header=None)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        _mod = e.modifiers()
        _key = e.key()
        if _mod & Qt.ControlModifier and _key == Qt.Key.Key_C:
            headers = _mod & Qt.ShiftModifier
            return self.copyToClipboard(headers)

        return super().keyPressEvent(e)

    def filter(self) -> FilterType | None:
        """Return the current filter."""
        return self._filter_slice

    def setFilter(self, sl: FilterType):
        """Set filter to the table view."""
        # NOTE: This method is also called when table needs initialization.

        self._filter_slice = sl
        data_sliced = self.tableSlice()

        if sl is None:
            self.model().df = data_sliced
        else:
            try:
                if callable(sl):
                    sl_filt = sl(data_sliced)
                else:
                    sl_filt = sl
                self.model().df = data_sliced[sl_filt]
            except Exception as e:
                self._filter_slice = None
                msg = f"Error in filter.\n\n{type(e).__name__} {e}\n\n Filter is reset."
                show_messagebox("error", "Error", msg, self)
        self.refresh()

    def refresh(self) -> None:
        qtable = self._qtable_view
        qtable.viewport().update()
        # headers have also to be updated.
        qtable.horizontalHeader().viewport().update()
        qtable.verticalHeader().viewport().update()
        return None


def _count_data_size(*args, **kwargs) -> float:
    total_nbytes = 0
    for arg in args:
        total_nbytes += _getsizeof(arg)
    for v in kwargs.values():
        total_nbytes += _getsizeof(v)
    return total_nbytes


def _getsizeof(obj) -> float:
    if isinstance(obj, pd.DataFrame):
        nbytes = obj.memory_usage(deep=True).sum()
    elif isinstance(obj, pd.Series):
        nbytes = obj.memory_usage(deep=True)
    elif isinstance(obj, np.ndarray):
        nbytes = obj.nbytes
    elif isinstance(obj, (list, tuple, set)):
        nbytes = sum(_getsizeof(x) for x in obj)
    elif isinstance(obj, dict):
        nbytes = sum(_getsizeof(x) for x in obj.values())
    else:
        nbytes = 1  # approximate
    return nbytes


class QMutableTable(QBaseTable):
    itemChangedSignal = Signal(ItemInfo)
    rowChangedSignal = Signal(HeaderInfo)
    columnChangedSignal = Signal(HeaderInfo)
    selectionChangedSignal = Signal(list)
    _data_raw: pd.DataFrame

    _mgr = UndoManager(measure=_count_data_size, maxsize=1e7)

    def __init__(
        self, parent: QtW.QWidget | None = None, data: pd.DataFrame | None = None
    ):
        super().__init__(parent, data)
        self._editable = False
        self.model().dataEdited.connect(self.setDataFrameValue)

        # header editing signals
        self._qtable_view.horizontalHeader().sectionDoubleClicked.connect(
            self.editHorizontalHeader
        )
        self._qtable_view.verticalHeader().sectionDoubleClicked.connect(
            self.editVerticalHeader
        )

    def tableShape(self) -> tuple[int, int]:
        model = self.model()
        nr = model.rowCount()
        nc = model.columnCount()
        return (nr, nc)

    def tableSlice(self) -> pd.DataFrame:
        # TODO: just for now!!
        return self._data_raw

    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value before updating DataFrame."""
        return value

    @overload
    def setDataFrameValue(self, r: int, c: int, value: Any) -> None:
        ...

    @overload
    def setDataFrameValue(self, r: slice, c: slice, value: pd.DataFrame) -> None:
        ...

    def setDataFrameValue(self, r, c, value) -> None:
        data = self._data_raw

        # convert values
        if isinstance(r, int) and isinstance(c, int):
            _value = self.convertValue(r, c, value)
        elif isinstance(r, slice) and isinstance(c, slice):
            _value: pd.DataFrame = value
            if _value.size == 1:
                v = _value.values[0, 0]
                _value = data.iloc[r, c].copy()
                for _ir, _r in enumerate(range(r.start, r.stop)):
                    for _ic, _c in enumerate(range(c.start, c.stop)):
                        _value.iloc[_ir, _ic] = self.convertValue(_r, _c, v)
            else:
                for _ir, _r in enumerate(range(r.start, r.stop)):
                    for _ic, _c in enumerate(range(c.start, c.stop)):
                        _value.iloc[_ir, _ic] = self.convertValue(
                            _r, _c, _value.iloc[_ir, _ic]
                        )
        else:
            raise TypeError

        if self._filter_slice is None:
            r0 = r
        else:
            if callable(self._filter_slice):
                sl = self._filter_slice(data)
            else:
                sl = self._filter_slice

            spec = np.where(sl)[0].tolist()
            r0 = spec[r]
            self.model().updateValue(r, c, _value)
        _old_value = data.iloc[r0, c]

        # emit item changed signal if value changed
        # NOTE pd.NA == x returns pd.NA, not False
        emit = False
        if isinstance(_value, pd.DataFrame):
            emit = True

        elif pd.isna(_value):
            if not pd.isna(_old_value):
                emit = True
        else:
            if pd.isna(_old_value) or _value != _old_value:
                emit = True

        if emit:
            self._set_value(r0, c, _value, _old_value)
            self.itemChangedSignal.emit(ItemInfo(r0, c, _value, _old_value))
        return None

    @_mgr.command
    def _set_value(self, r, c, value, old_value):
        self._data_raw.iloc[r, c] = value
        self.refresh()
        return None

    @_set_value.undo_def
    def _set_value(self, r, c, value, old_value):
        self._data_raw.iloc[r, c] = old_value
        self.refresh()
        return None

    def editability(self) -> bool:
        """Return the editability of the table."""
        return self._editable

    def setEditability(self, editable: bool):
        """Set the editability of the table."""
        if editable:
            self._qtable_view.setEditTriggers(_EDITABLE)
        else:
            self._qtable_view.setEditTriggers(_READ_ONLY)
        self._editable = editable

    def connectItemChangedSignal(self, *slots: tuple[Callable, Callable, Callable]):
        slot_val, slot_row, slot_col = slots
        self.itemChangedSignal.connect(slot_val)
        self.rowChangedSignal.connect(slot_row)
        self.columnChangedSignal.connect(slot_col)
        return None

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        _mod = e.modifiers()
        _key = e.key()
        if _mod & Qt.KeyboardModifier.ControlModifier and _key == Qt.Key.Key_C:
            headers = _mod & Qt.KeyboardModifier.ShiftModifier
            return self.copyToClipboard(headers)
        elif _mod & Qt.KeyboardModifier.ControlModifier and _key == Qt.Key.Key_V:
            return self.pasteFromClipBoard()
        elif _mod == Qt.KeyboardModifier.NoModifier and _key in (
            Qt.Key.Key_Delete,
            Qt.Key.Key_Backspace,
        ):
            return self.deleteValues()
        elif _mod == Qt.KeyboardModifier.ControlModifier and _key == Qt.Key.Key_Z:
            self._mgr.undo()
        elif _mod == Qt.KeyboardModifier.ControlModifier and _key == Qt.Key.Key_Y:
            self._mgr.redo()
        elif (
            _mod
            in (
                Qt.KeyboardModifier.NoModifier,
                Qt.KeyboardModifier.ShiftModifier,
            )
            and (Qt.Key.Key_Exclam <= _key <= Qt.Key.Key_ydiaeresis)
        ):
            # Enter editing mode
            qtable = self._qtable_view
            text = QtGui.QKeySequence(_key).toString()
            if _mod != Qt.KeyboardModifier.ShiftModifier:
                text = text.lower()
            self.model().setData(qtable.currentIndex(), text, Qt.ItemDataRole.EditRole)
            qtable.edit(qtable.currentIndex())
            focused_widget = QtW.QApplication.focusWidget()
            if isinstance(focused_widget, QtW.QLineEdit):
                focused_widget.deselect()
            return
        else:
            return super().keyPressEvent(e)

    def pasteFromClipBoard(self):
        """
        Paste data to table.

        This function supports many types of pasting.
        1. Single selection, single data in clipboard -> just paste
        2. Single selection, multiple data in clipboard -> paste starts from the selection position.
        3. Multiple selection, single data in clipboard -> paste the same value for all the selection.
        4. Multiple selection, multiple data in clipboard -> paste only if their shape is identical.

        Also, if data is filtrated, pasted data also follows the filtration.
        """
        selections = self.selections()
        n_selections = len(selections)
        if n_selections == 0 or not self.editability():
            return
        elif n_selections > 1:
            return show_messagebox(
                mode="error",
                title="Error",
                text="Cannot paste with multiple selections.",
                parent=self,
            )

        df = self.readClipBoard()

        # check size and normalize selection slices
        sel = selections[0]
        rrange, crange = sel
        rlen = rrange.stop - rrange.start
        clen = crange.stop - crange.start
        dr, dc = df.shape
        size = dr * dc

        if rlen * clen == 1 and size > 1:
            sel = (
                slice(rrange.start, rrange.start + dr),
                slice(crange.start, crange.start + dc),
            )

        elif size > 1 and (rlen, clen) != (dr, dc):
            # If selection is column-wide or row-wide, resize them
            model = self.model()
            if rlen == model.df.shape[0]:
                rrange = slice(0, dr)
                rlen = dr
            if clen == model.df.shape[1]:
                crange = slice(0, dc)
                clen = dc

            if (rlen, clen) != (dr, dc):
                return show_messagebox(
                    mode="error",
                    title="Error",
                    text=f"Shape mismatch between data in clipboard {(rlen, clen)} and "
                    f"destination {(dr, dc)}.",
                    parent=self,
                )
            else:
                sel = (rrange, crange)

        rsel, csel = sel

        # check dtype
        dtype_src = df.dtypes
        dtype_dst = self._data_raw.dtypes[csel]
        if any(a.kind != b.kind for a, b in zip(dtype_src.values, dtype_dst.values)):
            return show_messagebox(
                mode="error",
                title="Error",
                text=f"Data type mismatch between data in clipboard {list(dtype_src)} and "
                f"destination {list(dtype_dst)}.",
                parent=self,
            )

        # update table
        try:
            self.setDataFrameValue(rsel, csel, df)

        except Exception as e:
            show_messagebox(
                mode="error",
                title=e.__class__.__name__,
                text=str(e),
                parent=self,
            )
            raise e from None

        else:
            self.setSelections([sel])

        return None

    def deleteValues(self):
        """Replace selected cells with NaN."""
        selections = self.selections()
        for sel in selections:
            rsel, csel = sel
            nr = rsel.stop - rsel.start
            nc = csel.stop - csel.start
            dtypes = list(self._data_raw.dtypes[csel])
            df = pd.DataFrame(
                {c: pd.Series(np.full(nr, np.nan), dtype=dtypes[c]) for c in range(nc)},
            )
            self.setDataFrameValue(rsel, csel, df)

    def editHorizontalHeader(self, index: int):
        """Edit the horizontal header."""
        if not self.editability():
            return

        qtable = self._qtable_view
        _header = qtable.horizontalHeader()
        _line = QtW.QLineEdit(_header)
        edit_geometry = _line.geometry()
        edit_geometry.setHeight(_header.height())
        edit_geometry.setWidth(_header.sectionSize(index))
        edit_geometry.moveLeft(_header.sectionViewportPosition(index))
        _line.setGeometry(edit_geometry)
        _line.setHidden(False)
        _line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        column_axis = self.model().df.columns
        if index < column_axis.size:
            old_value = column_axis[index]
            text = str(old_value)
        else:
            old_value = None
            text = ""

        _line.setText(text)
        _line.setFocus()

        self._line = _line

        @_line.editingFinished.connect
        def _set_header_data():
            self._line.setHidden(True)
            value = self._line.text()
            if not value == old_value:
                self.setHorizontalHeaderValue(index, value)
                self.columnChangedSignal.emit(HeaderInfo(index, value, old_value))
            return None

        return None

    def editVerticalHeader(self, index: int):
        if not self.editability():
            return

        qtable = self._qtable_view
        _header = qtable.verticalHeader()
        _line = QtW.QLineEdit(_header)
        edit_geometry = _line.geometry()
        edit_geometry.setHeight(_header.sectionSize(index))
        edit_geometry.setWidth(_header.width())
        edit_geometry.moveTop(_header.sectionViewportPosition(index))
        _line.setGeometry(edit_geometry)
        _line.setHidden(False)

        index_axis = self.model().df.index

        if index < index_axis.size:
            old_value = index_axis[index]
            text = str(old_value)
        else:
            old_value = None
            text = ""

        _line.setText(str(text))
        _line.setFocus()
        _line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._line = _line

        @_line.editingFinished.connect
        def _set_header_data():
            self._line.setHidden(True)
            value = self._line.text()
            if not value == old_value:
                self.setVerticalHeaderValue(index, value)
                self.rowChangedSignal.emit(HeaderInfo(index, value, old_value))
            return None

        return None

    @_mgr.interface
    def setHorizontalHeaderValue(self, index: int, value: Any) -> None:
        qtable = self._qtable_view
        column_axis = self.model().df.columns
        _header = qtable.horizontalHeader()

        mapping = {column_axis[index]: value}

        self._data_raw.rename(columns=mapping, inplace=True)
        self.model().df.rename(columns=mapping, inplace=True)

        size_hint = _header.sectionSizeHint(index)
        if _header.sectionSize(index) < size_hint:
            _header.resizeSection(index, size_hint)
        self.refresh()
        return None

    @setHorizontalHeaderValue.server
    def setHorizontalHeaderValue(self, index: int, value: Any) -> Any:
        return (index, self.model().df.columns[index]), {}

    @_mgr.interface
    def setVerticalHeaderValue(self, index: int, value: Any) -> None:
        qtable = self._qtable_view
        index_axis = self.model().df.index
        _header = qtable.verticalHeader()

        mapping = {index_axis[index]: value}

        self._data_raw.rename(index=mapping, inplace=True)
        self.model().df.rename(index=mapping, inplace=True)
        _width_hint = _header.sizeHint().width()
        _header.resize(QtCore.QSize(_width_hint, _header.height()))
        self.refresh()
        return None

    @setVerticalHeaderValue.server
    def setVerticalHeaderValue(self, index: int, value: Any) -> Any:
        return (index, self.model().df.index[index]), {}


class QMutableSimpleTable(QMutableTable):
    """A mutable table with a single QTableView."""

    @property
    def _qtable_view(self) -> _QTableViewEnhanced:
        return self._qtable_view_

    def createQTableView(self):
        self._qtable_view_ = _QTableViewEnhanced()
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(_layout)
        self.layout().addWidget(self._qtable_view_)


class TableItemDelegate(QtW.QStyledItemDelegate):
    """Displays table widget items with properly formatted numbers."""

    def __init__(self, parent: QtCore.QObject | None = None, ndigits: int = 4) -> None:
        super().__init__(parent)
        self.ndigits = ndigits

    def displayText(self, value, locale):
        return super().displayText(self._format_number(value), locale)

    def createEditor(
        self, parent: QtW.QWidget, option, index: QtCore.QModelIndex
    ) -> QtW.QWidget:
        """Create different type of editors for different dtypes."""
        table = parent.parent().parent()
        if isinstance(table, QMutableTable):
            df = table.model().df
            row = index.row()
            col = index.column()
            if row >= df.shape[0] or col >= df.shape[1]:
                # out of bounds
                return super().createEditor(parent, option, index)

            dtype: np.dtype = df.dtypes[col]
            if dtype == "category":
                # use combobox for categorical data
                cbox = QtW.QComboBox(parent)
                choices = list(map(str, dtype.categories))
                cbox.addItems(choices)
                cbox.setCurrentIndex(choices.index(df.iat[row, col]))
                return cbox
            elif dtype == "bool":
                # use checkbox for boolean data
                cbox = QtW.QComboBox(parent)
                choices = ["True", "False"]
                cbox.addItems(choices)
                cbox.setCurrentIndex(0 if df.iat[row, col] else 1)
                return cbox
            elif dtype.kind == "M":
                dt = QtW.QDateTimeEdit(parent)
                dt.setDateTime(df.iat[row, col].to_pydatetime())
                return dt

        return super().createEditor(parent, option, index)

    def setEditorData(self, editor: QtW.QWidget, index: QtCore.QModelIndex) -> None:
        super().setEditorData(editor, index)
        if isinstance(editor, QtW.QComboBox):
            editor.showPopup()
        return None

    def setModelData(
        self,
        editor: QtW.QWidget,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ) -> None:
        if isinstance(editor, QtW.QDateTimeEdit):
            dt = editor.dateTime().toPyDateTime()
            model.setData(index, dt, Qt.ItemDataRole.EditRole)
        else:
            return super().setModelData(editor, model, index)

    # modified from magicgui
    def _format_number(self, text: str) -> str:
        """convert string to int or float if possible"""
        try:
            value: int | float | None = int(text)
        except ValueError:
            try:
                value = float(text)
            except ValueError:
                value = None

        ndigits = self.ndigits

        if isinstance(value, (int, float)):
            if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
                text = str(value) if isinstance(value, int) else f"{value:.{ndigits}f}"
            else:
                text = f"{value:.{ndigits-1}e}"

        return text
