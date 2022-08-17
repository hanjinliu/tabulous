from __future__ import annotations
from typing import Any, Callable, TYPE_CHECKING, cast
import warnings
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Signal, Qt

import numpy as np
import pandas as pd
from collections_undo import fmt

from ._model_base import AbstractDataFrameModel

from ..._undo import QtUndoManager, fmt_slice
from ..._keymap import QtKeys, QtKeyMap
from ....types import FilterType, ItemInfo, HeaderInfo, SelectionType, _Sliceable
from ....exceptions import SelectionRangeError, TableImmutableError

if TYPE_CHECKING:
    from ._delegate import TableItemDelegate
    from ._side_area import QTableSideArea
    from qtpy.QtCore import pyqtBoundSignal

# fmt: off
# Flags
_SCROLL_PER_PIXEL = QtW.QAbstractItemView.ScrollMode.ScrollPerPixel

# Built-in table view key press events
_TABLE_VIEW_KEY_SET = set()
for keys in ["Up", "Down", "Left", "Right", "Home", "End", "PageUp", "PageDown", "F2", "Escape",
             "Shift+Home", "Shift+End", "Shift+PageUp", "Shift+PageDown", "Ctrl+A"]:
    _TABLE_VIEW_KEY_SET.add(QtKeys(keys))
_TABLE_VIEW_KEY_SET = frozenset(_TABLE_VIEW_KEY_SET)

# fmt: on


class _QTableViewEnhanced(QtW.QTableView):
    selectionChangedSignal = Signal()
    rightClickedSignal = Signal(QtCore.QPoint)
    focusedSignal = Signal()
    resizedSignal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        if isinstance(parent, QBaseTable):
            self._parent_table = parent
        else:
            self._parent_table = None

        from ...._global_variables import table

        # settings
        self._font_size = table.font_size
        self._zoom = 1.0
        self._h_default = table.row_size
        self._w_default = table.column_size
        self._font = table.font

        self.setFont(QtGui.QFont(self._font, self._font_size))

        self._last_pos: QtCore.QPoint | None = None
        self._was_right_dragging: bool = False
        self._last_shift_on: tuple[int, int] = None
        vheader, hheader = self.verticalHeader(), self.horizontalHeader()

        vheader.resize(36, vheader.height())
        vheader.setMinimumSectionSize(0)
        hheader.setMinimumSectionSize(0)

        vheader.setDefaultSectionSize(self._h_default)
        hheader.setDefaultSectionSize(self._w_default)

        hheader.setSectionResizeMode(QtW.QHeaderView.ResizeMode.Fixed)
        vheader.setSectionResizeMode(QtW.QHeaderView.ResizeMode.Fixed)

        self.setVerticalScrollMode(_SCROLL_PER_PIXEL)
        self.setHorizontalScrollMode(_SCROLL_PER_PIXEL)

        from ._delegate import TableItemDelegate

        delegate = TableItemDelegate(parent=self)
        self.setItemDelegate(delegate)

    # fmt: off
    if TYPE_CHECKING:
        def model(self) -> AbstractDataFrameModel: ...
        def itemDelegate(self) -> TableItemDelegate: ...
    # fmt: on

    def copy(self, link: bool = True) -> _QTableViewEnhanced:
        """Make a copy of the table."""
        new = _QTableViewEnhanced(self.parentTable())
        if link:
            new.setModel(self.model())
            new.setSelectionModel(self.selectionModel())
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
        self.update()  # this is needed to update the selection rectangle
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

        if keys.has_shift():
            if self._last_shift_on is None:
                index = self.currentIndex()
                self._last_shift_on = index.row(), index.column()
        elif keys.has_key():
            self._last_shift_on = None

        if keys in _TABLE_VIEW_KEY_SET:
            return super().keyPressEvent(e)

        parent = self.parentTable()

        if keys.is_typing() and parent.isEditable():
            # Enter editing mode
            text = keys.key_string()
            if not keys.has_shift():
                text = text.lower()
            self.edit(self.currentIndex())
            focused_widget = QtW.QApplication.focusWidget()
            if isinstance(focused_widget, QtW.QLineEdit):
                focused_widget = cast(QtW.QLineEdit, focused_widget)
                focused_widget.setText(text)
                focused_widget.deselect()
            return

        if isinstance(parent, QBaseTable):
            parent.keyPressEvent(e)

    def zoom(self) -> float:
        """Get current zoom factor."""
        return self._zoom

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
        self.setSectionSize(int(self._w_default * value), int(self._h_default * value))

        # # Update stuff
        self._zoom = value
        self.viewport().update()
        self.horizontalHeader().viewport().update()
        self.verticalHeader().viewport().update()
        font = self.font()
        font.setPointSize(int(self._font_size * value))
        self.setFont(font)
        self.verticalHeader().setFont(font)
        self.horizontalHeader().setFont(font)
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

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        self.resizedSignal.emit()
        return super().resizeEvent(e)

    def paintEvent(self, event: QtGui.QPaintEvent):
        super().paintEvent(event)
        if not self.hasFocus():
            return
        sels = self.selectionModel().selection()
        nsel = len(sels)
        if nsel == 0:
            return
        sel = sels[nsel - 1]
        top_left = self.model().index(sel.top(), sel.left())
        bottom_right = self.model().index(sel.bottom(), sel.right())
        rect = self.visualRect(top_left) | self.visualRect(bottom_right)
        pen = QtGui.QPen(Qt.GlobalColor.darkBlue, 3)
        painter = QtGui.QPainter(self.viewport())
        painter.setPen(pen)
        painter.drawRect(rect)
        return None

    def parentTable(self) -> QBaseTable | None:
        parent = self._parent_table
        if not isinstance(parent, QBaseTable):
            parent = None
        return parent


class QTableHandle(QtW.QSplitterHandle):
    def __init__(self, o: Qt.Orientation, parent: QtW.QSplitter) -> None:
        super().__init__(o, parent)
        self._sizes = parent.sizes()

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent) -> None:
        """Collapse/expand side area."""
        parent = self.splitter()
        sizes = parent.sizes()
        if sizes[1] == 0:
            parent.setSizes(self._sizes)
        else:
            self._sizes = sizes
            parent.setSizes([1, 0])

        return super().mouseDoubleClickEvent(a0)


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

    selectionChangedSignal = Signal()
    _DEFAULT_EDITABLE = False
    _mgr = QtUndoManager()
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

        self._qtable_view.selectionChangedSignal.connect(
            self.selectionChangedSignal.emit
        )

        self._side_area: QTableSideArea = None
        self.model()._editable = self._DEFAULT_EDITABLE
        self.setStyleSheet(
            "QSplitter::handle:horizontal {"
            "    background-color: gray;"
            "    border: 0px;"
            "    width: 4px;"
            "    margin-top: 5px;"
            "    margin-bottom: 5px;"
            "    border-radius: 2px;}"
        )

    def createHandle(self) -> QTableHandle:
        """Create custom handle."""
        return QTableHandle(Qt.Orientation.Horizontal, self)

    # fmt: off
    if TYPE_CHECKING:
        def handle(self, pos: int) -> QTableHandle: ...
    # fmt: on

    @property
    def _qtable_view(self) -> _QTableViewEnhanced:
        raise NotImplementedError()

    def createQTableView(self) -> None:
        """Create QTableView."""
        raise NotImplementedError()

    def getDataFrame(self) -> pd.DataFrame:
        raise NotImplementedError()

    def setDataFrame(self, df: pd.DataFrame) -> None:
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
        return self._qtable_view.model()

    def setDataFrameValue(self, row: int, col: int, value: Any) -> None:
        raise TableImmutableError("Table is immutable.")

    def deleteValues(self) -> None:
        raise TableImmutableError("Table is immutable.")

    def isEditable(self) -> bool:
        """Return the editability of the table."""
        return False

    def setEditable(self, editable: bool):
        """Set the editability of the table."""
        if editable:
            raise TableImmutableError("Table is immutable.")

    def assignColumn(self, ds: pd.Series):
        raise TableImmutableError("Table is immutable.")

    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value before updating DataFrame."""
        return value

    def dataShown(self) -> pd.DataFrame:
        return self.model().df

    def precision(self) -> int:
        """Return table value precision."""
        return self.itemDelegate().ndigits

    def setPrecision(self, ndigits: int) -> None:
        """Set table value precision."""
        ndigits = int(ndigits)
        if ndigits <= 0:
            raise ValueError("Cannot set negative precision.")
        self.itemDelegate().ndigits = ndigits
        return None

    def connectSelectionChangedSignal(self, slot):
        self.selectionChangedSignal.connect(slot)
        return slot

    def selections(self) -> SelectionType:
        """Get list of selections as slicable tuples"""
        qtable = self._qtable_view
        selections = qtable.selectionModel().selection()

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
        selection_model = qtable.selectionModel()
        selection_model.blockSignals(True)
        qtable.clearSelection()
        selection_model.blockSignals(False)

        model = self.model()
        nr, nc = self.tableShape()
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
                selection_model.select(
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
            raise SelectionRangeError("Cannot copy selected range.")
        else:
            data = self.dataShown()
            if nr == 1:
                axis = 1
            else:
                axis = 0
            ref = pd.concat([data.iloc[sel] for sel in selections], axis=axis)
            ref.to_clipboard(index=headers, header=headers)

    def pasteFromClipBoard(self):
        raise TableImmutableError("Table is immutable.")

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

    @_mgr.interface
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
                raise ValueError("Error in filter. Filter is reset.") from e

        return self.refreshTable()

    @setFilter.server
    def setFilter(self, sl: FilterType):
        return (self.filter(),), {}

    @setFilter.set_formatter
    def _setFilter_fmt(self, sl):
        from ....widgets.filtering import ColumnFilter

        if isinstance(sl, ColumnFilter):
            return f"table.filter{sl._repr[2:]}"
        return f"table.filter = {sl!r}"

    def refreshTable(self) -> None:
        """Refresh table view."""
        qtable = self._qtable_view
        qtable.viewport().update()
        # headers have also to be updated.
        qtable.horizontalHeader().viewport().update()
        qtable.verticalHeader().viewport().update()
        return None

    def undoStackView(self, show: bool = True):
        out = self._mgr.widget()
        if show:
            self.addSideWidget(out, name="Undo stack")
        return out

    def addSideWidget(self, widget: QtW.QWidget, name: str = ""):
        """Add a widget to the side area of the table."""
        if self._side_area is None:
            from ._side_area import QTableSideArea

            area = QTableSideArea()
            self.addWidget(area)
            self._side_area = area

        self._side_area.addWidget(widget, name=name)
        self.setSizes([500, 200])
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
    selectionChangedSignal = Signal()
    _data_raw: pd.DataFrame
    NaN = np.nan

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

    def setDataFrameValue(self, r: _Sliceable, c: _Sliceable, value: Any) -> None:
        if not self.isEditable():
            raise TableImmutableError("Table is immutable.")
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
        if _was_changed(_value, _old_value) and self.isEditable():
            self._set_value(r0, c, r, c, value=_value, old_value=_old_value)
        return None

    @QBaseTable._mgr.undoable
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

    @_set_value.set_formatter
    def _set_value_fmt(self, r, c, r_ori, c_ori, value, old_value):
        _r = fmt_slice(r)
        _c = fmt_slice(c)
        if isinstance(value, pd.DataFrame):
            if value.size < 6:
                _val = str(value.values.tolist())
            else:
                _val = "..."
        else:
            _val = fmt.map_object(value)
        return f"df.iloc[{_r}, {_c}] = {_val}"

    @_set_value.set_formatter_inv
    def _set_value_fmt_inv(self, r, c, r_ori, c_ori, value, old_value):
        return self._set_value_fmt(r, c, r_ori, c_ori, old_value, value)

    def assignColumn(self, ds: pd.Series):
        if ds.name in self._data_raw.columns:
            ic = self._data_raw.columns.get_loc(ds.name)
            self.setDataFrameValue(
                slice(0, ds.size), slice(ic, ic + 1), pd.DataFrame(ds)
            )
        else:
            self.assignNewColumn(ds)

    @QBaseTable._mgr.undoable
    def assignNewColumn(self, ds: pd.Series):
        self._data_raw[ds.name] = ds
        self.setDataFrame(self._data_raw)

    @assignNewColumn.undo_def
    def assignNewColumn(self, ds: pd.Series):
        del self._data_raw[ds.name]
        self.setDataFrame(self._data_raw)

    def updateValue(self, r, c, value):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._data_raw.iloc[r, c] = value

        if self._filter_slice is not None:
            self.setFilter(self._filter_slice)
        self.refreshTable()

    def isEditable(self) -> bool:
        """Return the editability of the table."""
        return self.model()._editable

    @QBaseTable._mgr.interface
    def setEditable(self, editable: bool):
        """Set the editability of the table."""
        self.model()._editable = editable
        return None

    @setEditable.server
    def setEditable(self, editable: bool):
        return (self.isEditable(),), {}

    @setEditable.set_formatter
    def _setEditable_fmt(self, editable: bool):
        return f"table.editable = {editable}"

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
        if not self._keymap.press_key(keys):
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
            raise ValueError("Cannot paste to multiple selections.")

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
                raise SelectionRangeError(
                    f"Shape mismatch between data in clipboard {(rlen, clen)} and "
                    f"destination {(dr, dc)}."
                )
            else:
                sel = (rrange, crange)

        rsel, csel = sel

        # check dtype
        dtype_src = df.dtypes.values
        dtype_dst = self._data_raw.dtypes.values[csel]
        if any(a.kind != b.kind for a, b in zip(dtype_src, dtype_dst)):
            raise ValueError(
                f"Data type mismatch between data in clipboard {list(dtype_src)} and "
                f"destination {list(dtype_dst)}."
            )

        # update table
        self.setDataFrameValue(rsel, csel, df)
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
                {
                    c: pd.Series(np.full(nr, self.NaN), dtype=dtypes[c])
                    for c in range(nc)
                },
            )
            self.setDataFrameValue(rsel, csel, df)
        return None

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
            self.model().df.columns,
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
        """
        Prepare a line edit for editing the header.

        Parameters
        ----------
        header : QtW.QHeaderView
            The QHeaderView object to edit.
        size : tuple of int
            Size of line edit.
        topleft : tuple of int
            Coordinates of the top left corner of the line edit.
        signal : pyqtBoundSignal
            Signal to emit when the line edit is finished.
        index : int
            Index that is now being edited.
        df_axis : pd.Index
            Corresponding axis of the dataframe.
        """
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
            _line.editingFinished.disconnect()
            value = self._line.text()
            if not value == old_value:
                signal.emit(HeaderInfo(index, value, old_value))
            header.parent().setFocus()
            header.parent().clearSelection()
            self._line.setHidden(True)
            self._line = None
            return None

        return _line

    @QBaseTable._mgr.interface
    def setHorizontalHeaderValue(self, index: int, value: Any) -> None:
        qtable = self._qtable_view
        column_axis = self.dataShown().columns
        _header = qtable.horizontalHeader()

        mapping = {column_axis[index]: value}

        self._data_raw.rename(columns=mapping, inplace=True)
        self.model().df.rename(columns=mapping, inplace=True)

        size_hint = _header.sectionSizeHint(index)
        if _header.sectionSize(index) < size_hint:
            _header.resizeSection(index, size_hint)
        self.refreshTable()
        return None

    @setHorizontalHeaderValue.server
    def setHorizontalHeaderValue(self, index: int, value: Any) -> Any:
        return (index, self.dataShown().columns[index]), {}

    @setHorizontalHeaderValue.set_formatter
    def _setHorizontalHeaderValue_fmt(self, index: int, value: Any) -> Any:
        return f"columns[{index}] = {value!r}"

    @QBaseTable._mgr.interface
    def setVerticalHeaderValue(self, index: int, value: Any) -> None:
        qtable = self._qtable_view
        index_axis = self.dataShown().index
        _header = qtable.verticalHeader()

        mapping = {index_axis[index]: value}

        self._data_raw.rename(index=mapping, inplace=True)
        self.model().df.rename(index=mapping, inplace=True)
        _width_hint = _header.sizeHint().width()
        _header.resize(QtCore.QSize(_width_hint, _header.height()))
        self.refreshTable()
        return None

    @setVerticalHeaderValue.server
    def setVerticalHeaderValue(self, index: int, value: Any) -> Any:
        return (index, self.model().df.index[index]), {}

    @setVerticalHeaderValue.set_formatter
    def _setVerticalHeaderValue_fmt(self, index: int, value: Any) -> Any:
        return f"index[{index}] = {value!r}"

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


def _was_changed(val: Any, old_val: Any) -> bool:
    # NOTE pd.NA == x returns pd.NA, not False
    out = False
    if isinstance(val, pd.DataFrame):
        out = True

    elif pd.isna(val):
        if not pd.isna(old_val):
            out = True
    else:
        if pd.isna(old_val) or val != old_val:
            out = True
    return out
