from __future__ import annotations
from typing import Any, Callable, TYPE_CHECKING
import warnings
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Signal, Qt

import numpy as np
import pandas as pd

from collections_undo import UndoManager
from ._model_base import AbstractDataFrameModel

from ..._utils import show_messagebox
from ..._keymap import QtKeys, QtKeyMap
from ....types import FilterType, ItemInfo, HeaderInfo, SelectionType, _Sliceable

if TYPE_CHECKING:
    from ._delegate import TableItemDelegate
    from qtpy.QtCore import pyqtBoundSignal
    from typing_extensions import Self

# fmt: off
# Flags
_SCROLL_PER_PIXEL = QtW.QAbstractItemView.ScrollMode.ScrollPerPixel

# Built-in table view key press events
_TABLE_VIEW_KEY_SET = set()
for keys in ["Up", "Down", "Left", "Right", "Home", "End", "PageUp", "PageDown", "F2", "Escape",
             "Shift+Up", "Shift+Down", "Shift+Left", "Shift+Right", "Shift+Home", "Shift+End",
             "Shift+PageUp", "Shift+PageDown", "Ctrl+A"]:
    _TABLE_VIEW_KEY_SET.add(QtKeys(keys))
_TABLE_VIEW_KEY_SET = frozenset(_TABLE_VIEW_KEY_SET)

# fmt: on


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


class _QTableViewEnhanced(QtW.QTableView):
    selectionChangedSignal = Signal()
    rightClickedSignal = Signal(QtCore.QPoint)
    focusedSignal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        if isinstance(parent, QBaseTable):
            self._parent_table = parent
        else:
            self._parent_table = None
        self._last_pos: QtCore.QPoint | None = None
        self._was_right_dragging: bool = False
        vheader, hheader = self.verticalHeader(), self.horizontalHeader()
        self.setFrameStyle(QtW.QFrame.Shape.Box)
        vheader.setFrameStyle(QtW.QFrame.Shape.Box)
        hheader.setFrameStyle(QtW.QFrame.Shape.Box)
        vheader.resize(16, vheader.height())
        self.setStyleSheet("QHeaderView::section { border: 1px solid black}")
        vheader.setMinimumSectionSize(0)
        hheader.setMinimumSectionSize(0)

        vheader.setDefaultSectionSize(24)
        hheader.setDefaultSectionSize(100)

        hheader.setSectionResizeMode(QtW.QHeaderView.ResizeMode.Fixed)
        vheader.setSectionResizeMode(QtW.QHeaderView.ResizeMode.Fixed)

        self._initial_section_size = (
            hheader.defaultSectionSize(),
            vheader.defaultSectionSize(),
        )

        self.setVerticalScrollMode(_SCROLL_PER_PIXEL)
        self.setHorizontalScrollMode(_SCROLL_PER_PIXEL)
        self.setFrameStyle(QtW.QFrame.Shape.NoFrame)

    if TYPE_CHECKING:

        def model(self) -> AbstractDataFrameModel:
            ...

    def copy(self) -> _QTableViewEnhanced:
        """Make a copy of the table."""
        new = _QTableViewEnhanced(self.parentTable())
        new.setModel(self.model())
        new.setSelectionModel(self.selectionModel())
        new.setItemDelegate(self.itemDelegate())
        new.setZoom(self.zoom())
        new.setCurrentIndex(self.currentIndex())
        return new

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
        keys = QtKeys(e)
        if keys in _TABLE_VIEW_KEY_SET:
            return super().keyPressEvent(e)
        parent = self.parentTable()
        if isinstance(parent, QBaseTable):
            parent.keyPressEvent(e)

    def zoom(self) -> float:
        """Get current zoom factor."""
        return self.model()._zoom

    def setZoom(self, value: float) -> None:
        """Set zoom factor."""
        if not 0.25 <= value <= 2.0:
            raise ValueError("Zoom factor must between 0.25 and 2.0.")
        # To keep table at the same position.
        zoom_ratio = 1 / self.zoom() * value
        pos = self.verticalScrollBar().sliderPosition()
        self.verticalScrollBar().setSliderPosition(int(pos * zoom_ratio))
        pos = self.horizontalScrollBar().sliderPosition()
        self.horizontalScrollBar().setSliderPosition(int(pos * zoom_ratio))

        # # Zoom section size of headers
        h, v = self._initial_section_size
        self.setSectionSize(int(h * value), int(v * value))

        # # Update stuff
        self.model()._zoom = value
        self.viewport().update()
        self.horizontalHeader().viewport().update()
        self.verticalHeader().viewport().update()
        return

    def wheelEvent(self, e: QtGui.QWheelEvent) -> None:
        """Zoom in/out table."""
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            dt = e.angleDelta().y() / 120
            zoom = self.zoom() + 0.15 * dt
            self.setZoom(min(max(zoom, 0.25), 2.0))
            return None

        return super().wheelEvent(e)

    def sectionSize(self) -> tuple[int, int]:
        """Return current section size."""
        return (
            self.horizontalHeader().defaultSectionSize(),
            self.verticalHeader().defaultSectionSize(),
        )

    def setSectionSize(self, horizontal: int, vertical: int) -> None:
        """Update section size of headers."""
        self.verticalHeader().setDefaultSectionSize(vertical)
        self.horizontalHeader().setDefaultSectionSize(horizontal)
        return

    def focusInEvent(self, e: QtGui.QFocusEvent) -> None:
        self.focusedSignal.emit()
        return super().focusInEvent(e)

    def parentTable(self) -> QBaseTable | None:
        parent = self._parent_table
        if not isinstance(parent, QBaseTable):
            parent = None
        return parent


class QBaseTable(QtW.QSplitter):
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
    _mgr = UndoManager(measure=_count_data_size, maxsize=1e7)
    _keymap = QtKeyMap()

    def __init__(
        self, parent: QtW.QWidget | None = None, data: pd.DataFrame | None = None
    ):
        super().__init__(parent)
        self._filter_slice: FilterType | None = None
        self.setContentsMargins(0, 0, 0, 0)

        self.createQTableView()
        self.createModel()
        self.setDataFrame(data)

        from ._delegate import TableItemDelegate

        delegate = TableItemDelegate(parent=self)
        self._qtable_view.setItemDelegate(delegate)
        self._qtable_view.selectionChangedSignal.connect(
            lambda: self.selectionChangedSignal.emit(self.selections())
        )

        self._side_area = None
        self.model()._editable = self._DEFAULT_EDITABLE

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

    def dataShape(self) -> tuple[int, int]:
        return self.tableShape()

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

    def setDataFrameValue(self, row: int, col: int, value: Any) -> None:
        raise TypeError("Table is immutable.")

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

    def selections(self) -> SelectionType:
        """Get list of selections as slicable tuples"""
        qtable = self._qtable_view
        selections = qtable.selectionModel().selection()

        # selections = self.selectedRanges()
        out: SelectionType = []
        for i in range(len(selections)):
            sel = selections[i]
            r0 = sel.top()
            r1 = sel.bottom() + 1
            c0 = sel.left()
            c1 = sel.right() + 1
            out.append((slice(r0, r1), slice(c0, c1)))

        return out

    def setSelections(self, selections: SelectionType):
        """Set list of selections."""
        qtable = self._qtable_view
        qtable.clearSelection()

        model = self.model()
        nr, nc = model.df.shape
        try:
            for sel in selections:
                r, c = sel
                # if int is used instead of slice
                if not isinstance(r, slice):
                    _r = r.__index__()
                    if _r < 0:
                        _r += nr
                    r = slice(_r, _r + 1)
                if not isinstance(c, slice):
                    _c = c.__index__()
                    if _c < 0:
                        _c += nc
                    c = slice(_c, _c + 1)
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

    def pasteFromClipBoard(self):
        raise TypeError("Table is immutable.")

    def readClipBoard(self) -> pd.DataFrame:
        """Read clipboard data and return as pandas DataFrame."""
        return pd.read_clipboard(header=None)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if self._keymap.press_key(e):
            return
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

    def copy(self, link: bool = True) -> Self:
        if link:
            copy = self.__class__(self.parent(), self.getDataFrame())
            copy._qtable_view.setModel(self._qtable_view.model())
            copy._qtable_view.setSelectionModel(self._qtable_view.selectionModel())
        else:
            copy = self.__class__(self.parent(), self.getDataFrame())
        copy.setZoom(self.zoom())
        return copy

    def refresh(self) -> None:
        """Refresh table view."""
        qtable = self._qtable_view
        qtable.viewport().update()
        # headers have also to be updated.
        qtable.horizontalHeader().viewport().update()
        qtable.verticalHeader().viewport().update()
        return None

    def addSideWidget(self, widget: QtW.QWidget):
        if self._side_area is None:
            wdt = QtW.QWidget()
            wdt.setLayout(QtW.QVBoxLayout())
            self.addWidget(wdt)
            self._side_area = wdt
        self._side_area.layout().addWidget(widget)
        return None

    def setDualView(self, orientation: str = "horizontal"):
        """Set dual view."""
        from ._table_wrappers import QTableDualView

        if orientation == "vertical":
            qori = Qt.Orientation.Vertical
        elif orientation == "horizontal":
            qori = Qt.Orientation.Horizontal
        else:
            raise ValueError("orientation must be 'vertical' or 'horizontal'.")

        widget0 = self.widget(0)
        if widget0 is not self._qtable_view:
            widget0.setParent(None)
            widget0.deleteLater()
        self._qtable_view.setParent(None)
        dual = QTableDualView(self._qtable_view, qori)
        self.insertWidget(0, dual)
        return dual

    def setPopupView(self):
        """Set splash view."""
        from ._table_wrappers import QTablePopupView

        widget0 = self.widget(0)
        if widget0 is not self._qtable_view:
            widget0.setParent(None)
            widget0.deleteLater()

        self._qtable_view.setParent(None)
        view = QTablePopupView(self._qtable_view)
        self.insertWidget(0, view)
        view.exec()
        return view

    def resetViewMode(self):
        """Reset the view mode to the normal one."""
        widget0 = self.widget(0)
        if widget0 is not self._qtable_view:
            widget0.setParent(None)
            self.insertWidget(0, self._qtable_view)
            widget0.deleteLater()
        else:
            pass

        return None

    def moveToItem(self, row: int | None = None, column: int | None = None):
        if row is None:
            row = self._qtable_view.currentIndex().row()
        elif row < 0:
            row += self.dataShape()[0]

        if column is None:
            column = self._qtable_view.currentIndex().column()
        elif column < 0:
            column += self.dataShape()[1]

        self._qtable_view.selectionModel().setCurrentIndex(
            self.model().index(row, column),
            QtCore.QItemSelectionModel.SelectionFlag.Current,
        )
        return None


class QMutableTable(QBaseTable):
    """A mutable table widget."""

    itemChangedSignal = Signal(ItemInfo)
    rowChangedSignal = Signal(HeaderInfo)
    columnChangedSignal = Signal(HeaderInfo)
    selectionChangedSignal = Signal(list)
    _data_raw: pd.DataFrame

    def __init__(
        self, parent: QtW.QWidget | None = None, data: pd.DataFrame | None = None
    ):
        super().__init__(parent, data)
        self.model().dataEdited.connect(self.setDataFrameValue)

        # header editing signals
        self._qtable_view.horizontalHeader().sectionDoubleClicked.connect(
            self.editHorizontalHeader
        )
        self._qtable_view.verticalHeader().sectionDoubleClicked.connect(
            self.editVerticalHeader
        )
        self._mgr.clear()

        @self.rowChangedSignal.connect
        def _on_row_changed(info: HeaderInfo):
            return self.setVerticalHeaderValue(info.index, info.value)

        @self.columnChangedSignal.connect
        def _on_col_changed(info: HeaderInfo):
            return self.setHorizontalHeaderValue(info.index, info.value)

    def tableShape(self) -> tuple[int, int]:
        """Return the available shape of the table."""
        model = self.model()
        nr = model.rowCount()
        nc = model.columnCount()
        return (nr, nc)

    def tableSlice(self) -> pd.DataFrame:
        """Return 2D table for display."""
        return self._data_raw

    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value before updating DataFrame."""
        return value

    def setDataFrameValue(self, r: _Sliceable, c: _Sliceable, value: Any) -> None:
        data = self._data_raw

        # convert values
        if isinstance(r, slice) and isinstance(c, slice):
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
            _is_scalar = False
        else:
            _value = self.convertValue(r, c, value)
            _is_scalar = True

        # if table has filter, indices must be adjusted
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
        if not _is_scalar:
            _old_value: pd.DataFrame
            _old_value = _old_value.copy()  # this is needed for undo

        # emit item changed signal if value changed
        if _equal(_value, _old_value) and self.isEditable():
            self._set_value(r0, c, r, c, _value, _old_value)
        return None

    @QBaseTable._mgr.undoable(name="setDataFrameValue")
    def _set_value(self, r, c, r_ori, c_ori, value, old_value):
        self.updateValue(r, c, value)
        self.setSelections([(r_ori, c_ori)])
        self.itemChangedSignal.emit(ItemInfo(r, c, value, old_value))
        return None

    @_set_value.undo_def
    def _set_value(self, r, c, r_ori, c_ori, value, old_value):
        self.updateValue(r, c, old_value)
        self.setSelections([(r_ori, c_ori)])
        self.itemChangedSignal.emit(ItemInfo(r, c, old_value, value))
        return None

    def updateValue(self, r, c, value):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._data_raw.iloc[r, c] = value

        if self._filter_slice is not None:
            self.setFilter(self._filter_slice)
        self.refresh()

    def isEditable(self) -> bool:
        """Return the editability of the table."""
        return self.model()._editable

    def setEditable(self, editable: bool):
        """Set the editability of the table."""
        self.model()._editable = editable
        return None

    def toggleEditability(self) -> None:
        """Toggle editability of the table."""
        return self.setEditable(not self.isEditable())

    def connectItemChangedSignal(
        self,
        slot_val: Callable[[ItemInfo], None],
        slot_row: Callable[[HeaderInfo], None],
        slot_col: Callable[[HeaderInfo], None],
    ) -> None:
        self.itemChangedSignal.connect(slot_val)
        self.rowChangedSignal.connect(slot_row)
        self.columnChangedSignal.connect(slot_col)
        return None

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        keys = QtKeys(e)
        if self._keymap.press_key(keys):
            return

        if keys.is_typing() and self.isEditable():
            # Enter editing mode
            qtable = self._qtable_view
            text = keys.key_string()
            if not keys.has_shift():
                text = text.lower()
            qtable.edit(qtable.currentIndex())
            focused_widget = QtW.QApplication.focusWidget()
            if isinstance(focused_widget, QtW.QLineEdit):
                focused_widget.setText(text)
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
        if n_selections == 0 or not self.isEditable():
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
        dtype_src = df.dtypes.values
        dtype_dst = self._data_raw.dtypes.values[csel]
        if any(a.kind != b.kind for a, b in zip(dtype_src, dtype_dst)):
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
        if not self.isEditable():
            return None
        selections = self.selections()
        for sel in selections:
            rsel, csel = sel
            nr = rsel.stop - rsel.start
            nc = csel.stop - csel.start
            dtypes = list(self._data_raw.dtypes.values[csel])
            df = pd.DataFrame(
                {c: pd.Series(np.full(nr, np.nan), dtype=dtypes[c]) for c in range(nc)},
            )
            self.setDataFrameValue(rsel, csel, df)
        return None

    def copy(self, link: bool = True) -> Self:
        copy = super().copy(link=link)
        copy.setEditable(self.isEditable())
        return copy

    def editHorizontalHeader(self, index: int):
        """Edit the horizontal header."""
        if not self.isEditable():
            return

        qtable = self._qtable_view
        _header = qtable.horizontalHeader()
        self._prepare_header_line_edit(
            _header,
            (_header.sectionSize(index), _header.height()),
            (None, _header.sectionViewportPosition(index)),
            self.columnChangedSignal,
            index,
            self.model().df.index,
        )

        return None

    def editVerticalHeader(self, index: int):
        if not self.isEditable():
            return

        qtable = self._qtable_view
        _header = qtable.verticalHeader()
        self._prepare_header_line_edit(
            _header,
            (_header.width(), _header.sectionSize(index)),
            (_header.sectionViewportPosition(index), None),
            self.rowChangedSignal,
            index,
            self.model().df.index,
        )

        return None

    def _prepare_header_line_edit(
        self,
        header: QtW.QHeaderView,
        size: tuple[int, int],
        topleft: tuple[int, int],
        signal: pyqtBoundSignal,
        index: int,
        df_axis: pd.Index,
    ):
        _line = QtW.QLineEdit(header)
        width, height = size
        top, left = topleft
        edit_geometry = _line.geometry()
        edit_geometry.setHeight(height)
        edit_geometry.setWidth(width)
        if top is not None:
            edit_geometry.moveTop(top)
        if left is not None:
            edit_geometry.moveLeft(left)
        _line.setGeometry(edit_geometry)
        _line.setHidden(False)
        _line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if index < df_axis.size:
            old_value = df_axis[index]
            text = str(old_value)
        else:
            old_value = None
            text = ""

        _line.setText(text)
        _line.selectAll()
        _line.setFocus()

        self._line = _line

        @_line.editingFinished.connect
        def _set_header_data():
            if self._line is None:
                return None
            value = self._line.text()
            self._line.setHidden(True)
            if not value == old_value:
                signal.emit(HeaderInfo(index, value, old_value))
            self._line = None
            header.parent().setFocus()
            header.parent().clearSelection()
            return None

        return _line

    @QBaseTable._mgr.interface
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

    @QBaseTable._mgr.interface
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

    @QBaseTable._mgr.interface
    def setFilter(self, sl: FilterType):
        """Set filter to the table view. This operation is undoable."""
        return super().setFilter(sl)

    @setFilter.server
    def setFilter(self, sl: FilterType):
        return (self.filter(),), {}

    def undo(self) -> Any:
        """Undo last operation."""
        return self._mgr.undo()

    def redo(self) -> Any:
        """Redo last undo operation."""
        return self._mgr.redo()


class QMutableSimpleTable(QMutableTable):
    """A mutable table with a single QTableView."""

    @property
    def _qtable_view(self) -> _QTableViewEnhanced:
        return self._qtable_view_

    def createQTableView(self):
        self._qtable_view_ = _QTableViewEnhanced(self)
        self.addWidget(self._qtable_view_)
        return None


def _equal(val: Any, old_val: Any) -> bool:
    # NOTE pd.NA == x returns pd.NA, not False
    eq = False
    if isinstance(val, pd.DataFrame):
        eq = True

    elif pd.isna(val):
        if not pd.isna(old_val):
            eq = True
    else:
        if pd.isna(old_val) or val != old_val:
            eq = True
    return eq
