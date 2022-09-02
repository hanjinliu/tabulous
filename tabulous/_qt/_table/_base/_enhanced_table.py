from __future__ import annotations
from functools import lru_cache
from typing import TYPE_CHECKING, cast
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Signal, Qt

from ._item_model import AbstractDataFrameModel
from ._header_view import QHorizontalHeaderView, QVerticalHeaderView
from ._selection_model import RangesModel, SelectionModel
from ._table_base import QBaseTable

from ..._keymap import QtKeys

if TYPE_CHECKING:
    from ._delegate import TableItemDelegate
    from ..._mainwindow import _QtMainWidgetBase

# fmt: off
# Flags
_SCROLL_PER_PIXEL = QtW.QAbstractItemView.ScrollMode.ScrollPerPixel

# Built-in table view key press events
_TABLE_VIEW_KEY_SET = set()
for keys in ["Up", "Down", "Left", "Right", "Home", "End", "PageUp", "PageDown", "Escape",
             "Shift+Up", "Shift+Down", "Shift+Left", "Shift+Right",
             "Shift+Home", "Shift+End", "Shift+PageUp", "Shift+PageDown"]:
    _TABLE_VIEW_KEY_SET.add(QtKeys(keys))
_TABLE_VIEW_KEY_SET = frozenset(_TABLE_VIEW_KEY_SET)

# Selection colors
H_COLOR_W = QtGui.QColor(255, 96, 96, 86)
H_COLOR_B = QtGui.QColor(255, 0, 0, 86)
S_COLOR_W = Qt.GlobalColor.darkBlue
S_COLOR_B = Qt.GlobalColor.cyan

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

        # use custom selection model
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.NoSelection)
        self._selection_model = SelectionModel()
        self._highlight_model = RangesModel()

        self._last_pos: QtCore.QPoint | None = None
        self._was_right_dragging: bool = False

        vheader = QVerticalHeaderView()
        hheader = QHorizontalHeaderView()
        self.setVerticalHeader(vheader)
        self.setHorizontalHeader(hheader)

        vheader.selectionChangedSignal.connect(
            self._on_vertical_header_selection_change
        )
        hheader.selectionChangedSignal.connect(
            self._on_horizontal_header_selection_change
        )

        vheader.resize(36, vheader.height())
        vheader.setMinimumSectionSize(0)
        hheader.setMinimumSectionSize(0)

        vheader.setDefaultSectionSize(self._h_default)
        hheader.setDefaultSectionSize(self._w_default)

        self.setVerticalScrollMode(_SCROLL_PER_PIXEL)
        self.setHorizontalScrollMode(_SCROLL_PER_PIXEL)

        from ._delegate import TableItemDelegate

        delegate = TableItemDelegate(parent=self)
        self.setItemDelegate(delegate)

    # fmt: off
    if TYPE_CHECKING:
        def model(self) -> AbstractDataFrameModel: ...
        def itemDelegate(self) -> TableItemDelegate: ...
        def verticalHeader(self) -> QVerticalHeaderView: ...
        def horizontalHeader(self) -> QHorizontalHeaderView: ...
    # fmt: on

    def currentChanged(
        self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex
    ) -> None:
        r1 = current.row()
        c1 = current.column()

        # calculate the new current selection
        self._selection_model.drag_to(r1, c1)
        self.update()
        self.selectionChangedSignal.emit()
        if self.hasFocus():
            self.scrollTo(current)
        return None

    def copy(self, link: bool = True) -> _QTableViewEnhanced:
        """Make a copy of the table."""
        new = _QTableViewEnhanced(self.parentTable())
        if link:
            new.setModel(self.model())
            new.setSelectionModel(self.selectionModel())
            new._selection_model = self._selection_model
        new.setZoom(self.zoom())
        new.setCurrentIndex(self.currentIndex())
        return new

    def selectAll(self) -> None:
        """Override selectAll slot to update custom selections."""
        model = self.model()
        self.set_selections(
            [(slice(0, model.rowCount()), slice(0, model.columnCount()))]
        )
        return None

    def clear_selections(self) -> None:
        """Clear current selections."""
        self._selection_model.clear()
        self.update()
        return None

    def set_selections(self, selections: list[tuple[slice, slice]]) -> None:
        """Set current selections."""
        self._selection_model.set_ranges(selections)
        self.selectionChangedSignal.emit()
        self.update()
        return None

    def clear_highlights(self) -> None:
        """Clear current highlights."""
        self._highlight_model.clear()
        self.update()
        return None

    def set_highlights(self, highlights: list[tuple[slice, slice]]) -> None:
        """Set current highlights."""
        self._highlight_model.set_ranges(highlights)
        self.update()
        return None

    def _on_vertical_header_selection_change(self, r0: int, r1: int) -> None:
        """Set current row selections."""
        model = self.model()
        csel = slice(0, model.columnCount())
        _r0, _r1 = sorted([r0, r1])
        if len(self._selection_model) == 0:
            self._selection_model.append((slice(_r0, _r1 + 1), csel))
        else:
            self._selection_model.update_last((slice(_r0, _r1 + 1), csel))
        with self._selection_model.blocked():
            self.setCurrentIndex(model.index(r1, 0))
        self.update()
        return None

    def _on_horizontal_header_selection_change(self, c0: int, c1: int) -> None:
        """Set current row selections."""
        model = self.model()
        rsel = slice(0, self.model().rowCount())
        _c0, _c1 = sorted([c0, c1])
        if len(self._selection_model) == 0:
            self._selection_model.append((rsel, slice(_c0, _c1 + 1)))
        else:
            self._selection_model.update_last((rsel, slice(_c0, _c1 + 1)))
        with self._selection_model.blocked():
            self.setCurrentIndex(model.index(0, c1))
        self.update()
        return None

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        """Register clicked position"""
        # initialize just in case
        _selection_model = self._selection_model
        _selection_model.set_ctrl(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        _selection_model.set_shift(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if e.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(e.pos())
            r, c = index.row(), index.column()
            self._selection_model.drag_start(r, c)
        elif e.button() == Qt.MouseButton.RightButton:
            self._last_pos = e.pos()
            self._was_right_dragging = False
            return
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
        self._selection_model.drag_end()
        self._was_right_dragging = False
        return super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        index = self.indexAt(e.pos())
        if not index.isValid():
            return None
        from ._table_base import QMutableTable

        table = self.parentTable()
        if isinstance(table, QMutableTable):
            if table.isEditable():
                self.edit(index)
                self._selection_model.shift_end()
            else:
                table.tableStack().notifyEditability()
        return None

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        """Evoke parent keyPressEvent."""
        keys = QtKeys(e)

        if keys.has_shift():
            index = self.currentIndex()
            self._selection_model.shift_start(index.row(), index.column())
        elif keys.has_key():
            self._selection_model.shift_end()

        if keys in _TABLE_VIEW_KEY_SET:
            return super().keyPressEvent(e)

        parent = self.parentTable()

        if keys.is_typing() and parent.isEditable():
            # Enter editing mode
            text = keys.key_string()
            if not keys.has_shift():
                text = text.lower()
            self.edit(self.currentIndex())
            self._selection_model.shift_end()
            focused_widget = QtW.QApplication.focusWidget()
            if isinstance(focused_widget, QtW.QLineEdit):
                focused_widget = cast(QtW.QLineEdit, focused_widget)
                focused_widget.setText(text)
                focused_widget.deselect()
            return

        elif keys == "F2":
            if not parent.isEditable():
                return parent.tableStack().notifyEditability()
            return self.edit(self.currentIndex())

        if keys.has_ctrl():
            self._selection_model.set_ctrl(True)
        elif keys.has_key():
            self._selection_model.set_ctrl(False)

        if isinstance(parent, QBaseTable):
            return parent.keyPressEvent(e)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent) -> None:
        keys = QtKeys(a0)
        self._selection_model.set_ctrl(keys.has_ctrl())
        self._selection_model.set_shift(keys.has_shift())
        return super().keyReleaseEvent(a0)

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
        font = self.font()
        font.setPointSize(int(self._font_size * value))
        self.setFont(font)
        self.verticalHeader().setFont(font)
        self.horizontalHeader().setFont(font)
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

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        self.resizedSignal.emit()
        return super().resizeEvent(e)

    def paintEvent(self, event: QtGui.QPaintEvent):
        """Paint table and the selection."""
        super().paintEvent(event)
        focused = int(self.hasFocus())
        nsel = len(self._selection_model)
        painter = QtGui.QPainter(self.viewport())
        white_bg = self.parentViewer()._white_background

        # draw highlights
        h_color = H_COLOR_W if white_bg else H_COLOR_B

        for i, rect in enumerate(self._highlight_model.rangeRects(self)):
            painter.fillRect(rect, h_color)

        # draw selections
        s_color = S_COLOR_W if white_bg else S_COLOR_B
        for i, rect in enumerate(self._selection_model.rangeRects(self)):
            pen = QtGui.QPen(s_color, 2 + int(nsel == i + 1) * focused)
            painter.setPen(pen)
            painter.drawRect(rect)
        return None

    def parentTable(self) -> QBaseTable | None:
        """The parent QBaseTable widget."""
        parent = self._parent_table
        if not isinstance(parent, QBaseTable):
            parent = None
        return parent

    @lru_cache(maxsize=1)
    def parentViewer(self) -> _QtMainWidgetBase:
        """The parent table viewer widget."""
        parent = self.parentTable().parent()
        while not hasattr(parent, "_table_viewer"):
            parent = parent.parent()
        return parent
