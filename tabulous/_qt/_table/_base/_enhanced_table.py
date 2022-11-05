from __future__ import annotations

import weakref
import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Iterable, Iterator, cast, Literal
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Signal, Qt

from ._item_model import AbstractDataFrameModel
from ._header_view import QHorizontalHeaderView, QVerticalHeaderView
from ._table_base import QBaseTable, QMutableTable
from ._line_edit import QCellLiteralEdit

from ..._keymap import QtKeys
from ...._selection_model import RangesModel, SelectionModel, Index

if TYPE_CHECKING:
    from ._delegate import TableItemDelegate
    from ..._mainwindow import _QtMainWidgetBase

# Flags
_SCROLL_PER_PIXEL = QtW.QAbstractItemView.ScrollMode.ScrollPerPixel

# Selection colors
H_COLOR_W = QtGui.QColor(255, 96, 96, 86)
H_COLOR_B = QtGui.QColor(255, 0, 0, 86)
S_COLOR_W = Qt.GlobalColor.darkBlue
S_COLOR_B = Qt.GlobalColor.cyan
CUR_COLOR = QtGui.QColor(128, 128, 128, 108)
HOV_COLOR = QtGui.QColor(75, 75, 242, 80)

logger = logging.getLogger("tabulous")


class MouseTrack:
    """Info about the mouse position and button state"""

    def __init__(self):
        self.last_pos: QtCore.QPoint | None = None
        self.was_right_dragging: bool = False
        self.last_button: Literal["left", "right"] | None = None


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

        from ...._utils import get_config

        table = get_config().table  # get config

        # settings
        self._font_size = table.font_size
        self._zoom = 1.0
        self._h_default = table.row_size
        self._w_default = table.column_size
        self._font = table.font
        self.setFont(QtGui.QFont(self._font, self._font_size))
        self.setWordWrap(False)  # this disables eliding float text

        # use custom selection model
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.NoSelection)
        self._selection_model = SelectionModel(
            lambda: self.model().rowCount(),
            lambda: self.model().columnCount(),
        )
        self._selection_model.moving.connect(self._on_moving)
        self._selection_model.moved.connect(self._on_moved)
        self._highlight_model = RangesModel()

        # parameters for mouse tracking
        self._mouse_track = MouseTrack()

        # header settings
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

        # item delegate
        from ._delegate import TableItemDelegate

        delegate = TableItemDelegate(parent=self)
        self.setItemDelegate(delegate)
        self._update_all()

        # attributes relevant to in-cell calculation
        self._focused_widget_ref = None
        self._focused_widget = None
        from ...._eval import GraphManager

        self._ref_graphs = GraphManager()

    # fmt: off
    if TYPE_CHECKING:
        def model(self) -> AbstractDataFrameModel: ...
        def itemDelegate(self) -> TableItemDelegate: ...
        def verticalHeader(self) -> QVerticalHeaderView: ...
        def horizontalHeader(self) -> QHorizontalHeaderView: ...
    # fmt: on

    @property
    def _focused_widget(self) -> QtW.QWidget | None:
        """QWidget that force focusing after focus is moved to the table."""
        if self._focused_widget_ref is None:
            return None
        return self._focused_widget_ref()

    @_focused_widget.setter
    def _focused_widget(self, widget: QtW.QWidget | None) -> None:
        current = self._focused_widget

        if widget is None:
            self._focused_widget_ref = None
        else:
            self._focused_widget_ref = weakref.ref(widget)

        if current is not None:
            current.close()

    @_focused_widget.deleter
    def _focused_widget(self) -> None:
        self._focused_widget = None

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

    def _update_rect(self, rect: QtCore.QRect) -> None:
        rect.adjust(-2, -2, 2, 2)
        return self.viewport().update(rect)

    def _range_rect(self, rng: tuple[slice, slice]) -> QtCore.QRect:
        rsel, csel = rng
        model = self.model()
        rect = self.visualRect(model.index(rsel.start, csel.start))
        rect |= self.visualRect(model.index(rsel.stop - 1, csel.stop - 1))
        return rect

    def _on_moving(self, src: Index, dst: Index) -> None:
        if not self._selection_model.is_jumping():
            # clear all the multi-selections
            for sel in self._selection_model:
                self._update_rect(self._range_rect(sel))

        else:
            if len(self._selection_model) > 1:
                self._update_rect(self._range_rect(self._selection_model[-2]))

        if self._selection_model.is_moving_to_edge():
            if len(self._selection_model) > 0:
                self._update_rect(self._range_rect(self._selection_model[-1]))

        return None

    def _on_moved(self, src: Index, dst: Index) -> None:
        """Update the view."""
        model = self.model()
        index_src = model.index(*src.as_uint())
        index_dst = model.index(*dst.as_uint())
        if dst >= (0, 0):
            self.scrollTo(index_dst)

        # rect is the region that needs to be updated
        rect: QtCore.QRect = self.visualRect(index_dst)
        if not self._selection_model.is_jumping():
            rect |= self.visualRect(index_src)
        if sel := self._selection_model.current_range:
            rect |= self._range_rect(sel)
        if start := self._selection_model.start:
            rect |= self.visualRect(model.index(*start))

        if src.row < 0 or dst.row < 0:
            rect.setBottom(99999)
        if src.column < 0 or dst.column < 0:
            rect.setRight(99999)
        self._update_all(rect)

        self.selectionChangedSignal.emit()
        return None

    def copy(self, link: bool = True) -> _QTableViewEnhanced:
        """Make a copy of the table."""
        new = _QTableViewEnhanced(self.parentTable())
        if link:
            new.setModel(self.model())
            new._selection_model = self._selection_model
            new._selection_model.moving.connect(new._on_moving)
            new._selection_model.moved.connect(new._on_moved)
        new.setZoom(self.zoom())
        new._selection_model.current_index = self._selection_model.current_index
        return new

    def selectAll(self) -> None:
        """Override selectAll slot to update custom selections."""
        nr, nc = self.model().df.shape
        self.set_selections([(slice(0, nr), slice(0, nc))])
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
        self._mouse_track.last_pos = e.pos()
        if e.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(e.pos())
            if index.isValid():
                r, c = index.row(), index.column()
                self._selection_model.jump_to(r, c)
            self._mouse_track.last_button = "left"
        elif e.button() == Qt.MouseButton.RightButton:
            self._mouse_track.was_right_dragging = False
            self._mouse_track.last_button = "right"
            return
        _selection_model.set_shift(True)
        return super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        """Scroll table plane when mouse is moved with right click."""
        if self._mouse_track.last_button == "right":
            pos = e.pos()
            dy = pos.y() - self._mouse_track.last_pos.y()
            dx = pos.x() - self._mouse_track.last_pos.x()
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self._mouse_track.last_pos = pos
            self._mouse_track.was_right_dragging = True
        else:
            index = self.indexAt(e.pos())
            if index.isValid():
                r, c = index.row(), index.column()
                if self._selection_model.current_index != (r, c):
                    self._selection_model.move_to(r, c)
        return None

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        """Delete last position."""
        if (
            e.button() == Qt.MouseButton.RightButton
            and not self._mouse_track.was_right_dragging
        ):
            self.rightClickedSignal.emit(e.pos())
        self._mouse_track.last_pos = None
        self._mouse_track.last_button = None
        self._selection_model.set_shift(
            e.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )
        self._mouse_track.was_right_dragging = False
        if wdt := self._focused_widget:
            wdt.setFocus()
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
                if wdt := self._focused_widget:
                    wdt.setFocus()
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
                if wdt := self._focused_widget:
                    if isinstance(wdt, QCellLiteralEdit):
                        wdt = cast(QCellLiteralEdit, wdt)
                        wdt._self_focused = True
                    wdt.setFocus()
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
        self._selection_model.set_shift(
            keys.has_shift() or self._mouse_track.last_pos is not None
        )
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
        self._update_all()
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
        # initialize selection model state
        self._selection_model.set_ctrl(False)
        self._selection_model.set_shift(False)
        return super().focusInEvent(e)

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        self.resizedSignal.emit()
        return super().resizeEvent(e)

    def _get_selection_color(self):
        white_bg = self.parentViewer()._white_background
        return S_COLOR_W if white_bg else S_COLOR_B

    def _get_highlight_color(self):
        white_bg = self.parentViewer()._white_background
        return H_COLOR_W if white_bg else H_COLOR_B

    def _get_current_index_color(self):
        return CUR_COLOR

    def paintEvent(self, event: QtGui.QPaintEvent):
        """Paint table and the selection."""
        super().paintEvent(event)
        focused = int(self.hasFocus())
        nsel = len(self._selection_model)
        painter = QtGui.QPainter(self.viewport())

        # draw graphs
        if self._ref_graphs._to_be_shown:
            _df = self.model().df
            try:
                for graph in self._ref_graphs._to_be_shown:
                    for i, rect in enumerate(
                        self._rect_from_ranges(
                            sel.as_iloc_slices(_df) for sel in graph._sources
                        )
                    ):
                        pen = QtGui.QPen(h_color, 3)
                        painter.setPen(pen)
                        painter.drawRect(rect)
                    # TODO: destination
                    # for i, rect in enumerate(
                    #     self._rect_from_ranges(sel.as_iloc(_df) for sel in graph._sources)
                    # ):
                    #     pen = QtGui.QPen(h_color, 2)
                    #     painter.setPen(pen)
                    #     painter.drawRect(rect)
            except Exception as e:
                logger.debug(f"Failed to draw graph: {e}")

        # draw highlights
        h_color = self._get_highlight_color()
        for i, rect in enumerate(self._rect_from_ranges(self._highlight_model._ranges)):
            painter.fillRect(rect, h_color)

        # draw selections
        s_color = self._get_selection_color()
        for i, rect in enumerate(self._rect_from_ranges(self._selection_model._ranges)):
            pen = QtGui.QPen(s_color, 2 + int(nsel == i + 1) * focused)
            painter.setPen(pen)
            painter.drawRect(rect)

        # current index
        idx = self._selection_model.current_index
        if idx >= (0, 0):
            rect_cursor = self.visualRect(self.model().index(*idx))
            rect_cursor.adjust(1, 1, -1, -1)
            pen = QtGui.QPen(CUR_COLOR, 3)
            painter.setPen(pen)
            painter.drawRect(rect_cursor)

        # mouse hover
        mouse_idx = self.indexAt(self.viewport().mapFromGlobal(QtGui.QCursor.pos()))
        if mouse_idx.isValid():
            rect_cursor = self.visualRect(mouse_idx)
            rect_cursor.adjust(1, 1, -1, -1)
            pen = QtGui.QPen(HOV_COLOR, 2)
            painter.setPen(pen)
            painter.drawRect(rect_cursor)

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

    def _rect_from_ranges(
        self, ranges: Iterable[tuple[slice, slice]]
    ) -> Iterator[QtCore.QRect]:
        """Convert range models into rectangles."""
        model = self.model()
        for rr, cc in ranges:
            top_left = model.index(rr.start, cc.start)
            bottom_right = model.index(rr.stop - 1, cc.stop - 1)
            rect = self.visualRect(top_left) | self.visualRect(bottom_right)
            yield rect

    def _create_eval_editor(
        self, text: str | None = None, moveto: tuple[int, int] | None = None
    ) -> QCellLiteralEdit:
        if moveto is not None:
            self._selection_model.move_to(*moveto)
        index = self.model().index(*self._selection_model.current_index)
        if text is None:
            text = self.model().data(index, Qt.ItemDataRole.EditRole)
        if not isinstance(text, str):
            text = ""
        line = QCellLiteralEdit.from_table(self, text)
        line.show()
        line.setFocus()
        return line
