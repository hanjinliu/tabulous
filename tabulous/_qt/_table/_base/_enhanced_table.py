from __future__ import annotations
from functools import lru_cache
from typing import TYPE_CHECKING, Iterator, cast
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Signal, Qt

from ._item_model import AbstractDataFrameModel
from ._header_view import QHorizontalHeaderView, QVerticalHeaderView
from ...._selection_model import RangesModel, SelectionModel, Index
from ._table_base import QBaseTable, QMutableTable

from ..._keymap import QtKeys

if TYPE_CHECKING:
    from ._delegate import TableItemDelegate
    from ..._mainwindow import _QtMainWidgetBase

# fmt: off
# Flags
_SCROLL_PER_PIXEL = QtW.QAbstractItemView.ScrollMode.ScrollPerPixel

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
        self._selection_model = SelectionModel(
            lambda: self.model().rowCount(),
            lambda: self.model().columnCount(),
        )
        self._selection_model.moving.connect(self._on_moving)
        self._selection_model.moved.connect(self._on_moved)
        self._highlight_model = RangesModel()

        self._last_pos: QtCore.QPoint | None = None
        self._was_right_dragging: bool = False
        self._last_mouse_button: str | None = None

        vheader = QVerticalHeaderView()
        hheader = QHorizontalHeaderView()
        self.setVerticalHeader(vheader)
        self.setHorizontalHeader(hheader)

        vheader.resize(36, vheader.height())
        vheader.setMinimumSectionSize(5)
        hheader.setMinimumSectionSize(5)

        vheader.setDefaultSectionSize(self._h_default)
        hheader.setDefaultSectionSize(self._w_default)

        self.setVerticalScrollMode(_SCROLL_PER_PIXEL)
        self.setHorizontalScrollMode(_SCROLL_PER_PIXEL)

        from ._delegate import TableItemDelegate

        delegate = TableItemDelegate(parent=self)
        self.setItemDelegate(delegate)
        self._update_all()

    # fmt: off
    if TYPE_CHECKING:
        def model(self) -> AbstractDataFrameModel: ...
        def itemDelegate(self) -> TableItemDelegate: ...
        def verticalHeader(self) -> QVerticalHeaderView: ...
        def horizontalHeader(self) -> QHorizontalHeaderView: ...
    # fmt: on

    def _update_all(self, rect: QtCore.QRect | None = None) -> None:
        """repaint the table and the headers."""
        if rect is None:
            self.viewport().update()
        else:
            rect.adjust(-2, -2, 2, 2)
            self.viewport().update(rect)
        self.horizontalHeader().viewport().update()
        self.verticalHeader().viewport().update()
        return None

    def _on_moving(self, src: Index, dst: Index) -> None:
        if not self._selection_model.is_jumping():
            # clear all the multi-selections
            model = self.model()
            for sel in self._selection_model:
                rsel, csel = sel
                rect: QtCore.QRect = self.visualRect(
                    model.index(rsel.start, csel.start)
                )
                rect |= self.visualRect(model.index(rsel.stop - 1, csel.stop - 1))
                rect.adjust(-2, -2, 2, 2)
                self.viewport().update(rect)

            if self._selection_model._ctrl_on:
                rect: QtCore.QRect = self.visualRect(model.index(*src))
                rect.adjust(-2, -2, 2, 2)
                self.viewport().update(rect)

        return None

    def _on_moved(self, src: Index, dst: Index) -> None:
        """Update the view."""
        model = self.model()
        index_src = model.index(*src.as_uint())
        index_dst = model.index(*dst.as_uint())
        if dst >= (0, 0):
            self.scrollTo(index_dst)

        ctrl_on = self._selection_model._ctrl_on

        # rect is the region that needs to be updated
        rect = self.visualRect(index_dst)
        if not ctrl_on:
            rect |= self.visualRect(index_src)

        if (sel := self._selection_model.current_range) is not None:
            rsel, csel = sel
            rect |= self.visualRect(model.index(rsel.start, csel.start))
            rect |= self.visualRect(model.index(rsel.stop - 1, csel.stop - 1))
        if self._selection_model._selection_start is not None:
            rect |= self.visualRect(
                model.index(*self._selection_model._selection_start)
            )

        if src.row < 0 or dst.row < 0:
            rect.setBottom(99999)
        if src.column < 0 or dst.column < 0:
            rect.setRight(99999)
        self._update_all(rect)

        return None

    def copy(self, link: bool = True) -> _QTableViewEnhanced:
        """Make a copy of the table."""
        new = _QTableViewEnhanced(self.parentTable())
        if link:
            new.setModel(self.model())
            new._selection_model = self._selection_model
            new._selection_model.moved.connect(new._on_moved)
        new.setZoom(self.zoom())
        new._selection_model.current_index = self._selection_model.current_index
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
        self._update_all()
        return None

    def set_selections(self, selections: list[tuple[slice, slice]]) -> None:
        """Set current selections."""
        self._selection_model.set_ranges(selections)
        self.selectionChangedSignal.emit()
        self._update_all()
        return None

    def clear_highlights(self) -> None:
        """Clear current highlights."""
        self._highlight_model.clear()
        self._update_all()
        return None

    def set_highlights(self, highlights: list[tuple[slice, slice]]) -> None:
        """Set current highlights."""
        self._highlight_model.set_ranges(highlights)
        self._update_all()
        return None

    def _edit_current(self) -> None:
        """Enter edit mode for current cell."""
        index = self.model().index(*self._selection_model.current_index)
        return self.edit(index)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        """Register clicked position"""
        # initialize just in case
        _selection_model = self._selection_model
        _selection_model.set_ctrl(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self._last_pos = e.pos()
        if e.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(e.pos())
            if index.isValid():
                r, c = index.row(), index.column()
                self._selection_model.jump_to(r, c)
            self._last_mouse_button = "left"
        elif e.button() == Qt.MouseButton.RightButton:
            self._was_right_dragging = False
            self._last_mouse_button = "right"
            return
        _selection_model.set_shift(True)
        return super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        """Scroll table plane when mouse is moved with right click."""
        if self._last_mouse_button == "right":
            pos = e.pos()
            dy = pos.y() - self._last_pos.y()
            dx = pos.x() - self._last_pos.x()
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self._last_pos = pos
            self._was_right_dragging = True
        else:
            index = self.indexAt(e.pos())
            if index.isValid():
                r, c = index.row(), index.column()
                if self._selection_model.current_index != (r, c):
                    self._selection_model.move_to(r, c)
        return None

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        """Delete last position."""
        if e.button() == Qt.MouseButton.RightButton and not self._was_right_dragging:
            self.rightClickedSignal.emit(e.pos())
        self._last_pos = None
        self._last_mouse_button = None
        self._selection_model.set_shift(
            e.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )
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
                self._selection_model.set_shift(False)
            else:
                table.tableStack().notifyEditability()
        return None

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        """Evoke parent keyPressEvent."""
        keys = QtKeys(e)

        sel_mod = self._selection_model

        if keys.has_shift():
            sel_mod.set_shift(True)
        else:
            sel_mod.set_shift(False)
            if keys.has_key():
                sel_mod.reset()

        parent = self.parentTable()

        if keys.is_typing() and parent.isEditable():
            # First check if either header is selected. If not, then edit
            # the current table cell.
            parent = cast(QMutableTable, parent)
            sel_mod.set_shift(False)
            sel_mod.reset()

            if sel_mod.current_index.row < 0:
                focused_widget = parent.editHorizontalHeader(
                    sel_mod.current_index.column
                )

            elif sel_mod.current_index.column < 0:
                focused_widget = parent.editVerticalHeader(sel_mod.current_index.row)

            else:
                self._edit_current()
                focused_widget = QtW.QApplication.focusWidget()

            if isinstance(focused_widget, QtW.QLineEdit):
                focused_widget = cast(QtW.QLineEdit, focused_widget)
                focused_widget.setText(keys.key_string(check_shift=True))
                focused_widget.deselect()
            return None

        elif keys == "F2":
            if not parent.isEditable():
                return parent.tableStack().notifyEditability()
            parent = cast(QMutableTable, parent)

            if sel_mod.current_index.row < 0:
                parent.editHorizontalHeader(sel_mod.current_index.column)
            elif sel_mod.current_index.column < 0:
                parent.editVerticalHeader(sel_mod.current_index.row)
            else:
                self._edit_current()
            return None

        if keys.has_ctrl():
            sel_mod.set_ctrl(True)
        elif keys.has_key():
            sel_mod.set_ctrl(False)

        if isinstance(parent, QBaseTable):
            return parent.keyPressEvent(e)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent) -> None:
        keys = QtKeys(a0)
        self._selection_model.set_ctrl(keys.has_ctrl())
        self._selection_model.set_shift(keys.has_shift() or self._last_pos is not None)
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

        for i, rect in enumerate(self.rectFromRanges(self._highlight_model)):
            painter.fillRect(rect, h_color)

        # draw selections
        s_color = S_COLOR_W if white_bg else S_COLOR_B
        for i, rect in enumerate(self.rectFromRanges(self._selection_model)):
            pen = QtGui.QPen(s_color, 2 + int(nsel == i + 1) * focused)
            painter.setPen(pen)
            painter.drawRect(rect)

        # current index
        idx = self._selection_model.current_index
        if idx >= (0, 0):
            rect_current = self.visualRect(self.model().index(*idx))
            rect_current.adjust(2, 2, -2, -2)
            pen = QtGui.QPen(QtGui.QColor(128, 128, 128, 108), 4)
            painter.setPen(pen)
            painter.drawRect(rect_current)

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

    def rectFromRanges(self, ranges_model: RangesModel) -> Iterator[QtCore.QRect]:
        """Convert range models into rectangles."""
        model = self.model()
        for rr, cc in ranges_model._ranges:
            top_left = model.index(rr.start, cc.start)
            bottom_right = model.index(rr.stop - 1, cc.stop - 1)
            rect = self.visualRect(top_left) | self.visualRect(bottom_right)
            yield rect
