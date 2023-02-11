from __future__ import annotations

import weakref
import logging
from typing import TYPE_CHECKING, Iterable, Iterator, cast, Literal
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Signal, Qt, Property

from ._item_model import AbstractDataFrameModel
from ._header_view import QHorizontalHeaderView, QVerticalHeaderView
from ._table_base import QBaseTable, QMutableTable
from ._line_edit import QCellLiteralEdit, QCellLabelEdit

from tabulous._keymap import QtKeys
from tabulous._selection_model import RangesModel, SelectionModel, Index

if TYPE_CHECKING:
    from ._delegate import TableItemDelegate
    from tabulous._qt._mainwindow import _QtMainWidgetBase
    from tabulous._map_model import SlotRefMapping
    from tabulous._utils import TabulousConfig

# Flags
_SCROLL_PER_PIXEL = QtW.QAbstractItemView.ScrollMode.ScrollPerPixel

# Selection colors
CUR_COLOR = QtGui.QColor(128, 128, 128, 108)
HOV_COLOR = QtGui.QColor(75, 75, 242, 80)

logger = logging.getLogger("tabulous")


class MouseTrack:
    """Info about the mouse position and button state"""

    def __init__(self):
        self.last_rightclick_pos: QtCore.QPoint | None = None
        self.was_right_dragging: bool = False
        self.last_button: Literal["left", "right"] | None = None


class _EventFilter(QtCore.QObject):
    """An event filter for text completion by tab."""

    def eventFilter(self, o: _QTableViewEnhanced, e: QtCore.QEvent):
        _type = e.type()
        if _type == QtCore.QEvent.Type.KeyPress:
            e = cast(QtGui.QKeyEvent, e)
            if e.key() == Qt.Key.Key_Tab:
                if e.modifiers() == Qt.KeyboardModifier.NoModifier:
                    o._tab_clicked()
                    return True
        elif _type == QtCore.QEvent.Type.StyleChange:
            pass  # TODO: do something in the future
        return False


class _QTableViewEnhanced(QtW.QTableView):
    selectionChangedSignal = Signal()
    rightClickedSignal = Signal(QtCore.QPoint)
    focusedSignal = Signal()
    resizedSignal = Signal()

    _focused_widget_ref: weakref.ReferenceType[QtW.QWidget] = None

    _table_map: SlotRefMapping

    def __init__(self, parent=None):
        super().__init__(parent)
        if isinstance(parent, QBaseTable):
            self._parent_table = parent
        else:
            self._parent_table = None

        self._zoom = 1.0
        self.setWordWrap(False)  # this disables eliding float text
        self.load_config()

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

        # event filter
        self._event_filter = _EventFilter(self)
        self.installEventFilter(self._event_filter)

        # the source ranges of in-cell slot are drawed or not
        self._current_drawing_slot_ranges = None

        # initialize with dummy mapping
        from tabulous._map_model import DummySlotRefMapping

        self._table_map = DummySlotRefMapping()

        # initialize colors
        self._selection_color = QtGui.QColor(120, 120, 170, 255)
        self._highlight_color = QtGui.QColor(255, 0, 0, 86)

    # fmt: off
    if TYPE_CHECKING:
        def model(self) -> AbstractDataFrameModel: ...
        def itemDelegate(self) -> TableItemDelegate: ...
        def verticalHeader(self) -> QVerticalHeaderView: ...
        def horizontalHeader(self) -> QHorizontalHeaderView: ...
    # fmt: on

    def load_config(self, cfg: TabulousConfig | None = None) -> None:
        from tabulous._utils import get_config

        if cfg is None:
            cfg = get_config()

        table = cfg.table

        # settings
        self._font_size = table.font_size
        self._h_default = table.row_size
        self._w_default = table.column_size
        self._font = table.font
        qfont = QtGui.QFont(self._font, int(self._zoom * self._font_size))
        self.setFont(qfont)
        self.horizontalHeader().setFont(qfont)
        self.verticalHeader().setFont(qfont)
        self._update_all()

    @property
    def _focused_widget(self) -> QtW.QWidget | None:
        """QWidget that force focusing after focus is moved to the table."""
        if self.__class__._focused_widget_ref is None:
            return None
        return self.__class__._focused_widget_ref()

    @_focused_widget.setter
    def _focused_widget(self, widget: QtW.QWidget | None) -> None:
        current = self._focused_widget

        if widget is None:
            self.__class__._focused_widget_ref = None
        else:
            self.__class__._focused_widget_ref = weakref.ref(widget)

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

    def _tab_clicked(self) -> None:
        r, c = self._selection_model.current_index
        if c == self.model().columnCount() - 1:
            if r < self.model().rowCount() - 1:
                self._selection_model.move_to(r + 1, 0)
            else:
                return None
        else:
            self._selection_model.move(0, 1)
        return None

    def _on_moving(self, src: Index, dst: Index) -> None:
        _need_update_all = self._current_drawing_slot_ranges is not None

        _nr, _nc = self.parentTable().dataShape()
        _r0, _c0 = dst
        new_status_tip = ""
        if _r0 < _nr and _c0 < _nc:
            _r0 = self.parentTable()._proxy.get_source_index(_r0)
            if slot := self._table_map.get_by_dest((_r0, _c0), None):
                self._current_drawing_slot_ranges = slot.range
                new_status_tip = f"<b><code>{slot.as_literal(dest=True)}</code></b>"
                _need_update_all = True
            else:
                self._current_drawing_slot_ranges = None

        if qviewer := self.parentViewer():
            qviewer._table_viewer.status = new_status_tip

        if _need_update_all:
            self._update_all()
            return None

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
        if dst >= (0, 0) and self.hasFocus():
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
            rect.setBottom(999999)
        if src.column < 0 or dst.column < 0:
            rect.setRight(999999)

        self.selectionChangedSignal.emit()

        self._update_all(rect)
        return None

    def copy(self, link: bool = True) -> _QTableViewEnhanced:
        """Make a copy of the table."""
        new = _QTableViewEnhanced(self.parentTable())
        if link:
            new.setModel(self.model())
            new._selection_model = self._selection_model
            new._selection_model.moving.connect(new._on_moving)
            new._selection_model.moved.connect(new._on_moved)
            new._table_map = self._table_map
        new.setZoom(self.zoom())
        new._selection_model.current_index = self._selection_model.current_index
        return new

    def selectAll(self) -> None:
        """Override selectAll slot to update custom selections."""
        nr, nc = self.model().df.shape
        if nr * nc > 0:
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

    def _edit_current(self) -> QCellLiteralEdit | None:
        """Enter edit mode for current cell."""
        index = self.model().index(*self._selection_model.current_index)
        self.edit(index)
        if editor := self._focused_widget:
            if isinstance(editor, QCellLiteralEdit):
                editor = cast(QCellLiteralEdit, editor)
                editor._on_text_changed(editor.text())
                editor._self_focused = True
            editor.setFocus()
        return editor

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        """Register clicked position"""
        # initialize just in case

        _selection_model = self._selection_model
        _selection_model.set_ctrl(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self._mouse_track.last_rightclick_pos = e.pos()
        if e.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(e.pos())
            if index.isValid():
                r, c = index.row(), index.column()
                self._selection_model.jump_to(r, c)
            else:
                # if outside the table is clicked, close the editor
                if isinstance(self._focused_widget, QCellLiteralEdit):
                    line = cast(QCellLiteralEdit, self._focused_widget)
                    line.eval_and_close()
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
            dy = pos.y() - self._mouse_track.last_rightclick_pos.y()
            dx = pos.x() - self._mouse_track.last_rightclick_pos.x()
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self._mouse_track.last_rightclick_pos = pos
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
        self._mouse_track.last_rightclick_pos = None
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
                if stack := table.tableStack():
                    stack.notifyEditability()
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
                focused_widget = self._edit_current()

            if isinstance(focused_widget, QtW.QLineEdit):
                focused_widget = cast(QtW.QLineEdit, focused_widget)
                focused_widget.setText(keys.key_string(check_shift=True))
                focused_widget.deselect()

            return None

        elif keys == "F2":
            if not parent.isEditable():
                if stack := parent.tableStack():
                    stack.notifyEditability()
                return None
            parent = cast(QMutableTable, parent)

            if sel_mod.current_index.row < 0:
                parent.editHorizontalHeader(sel_mod.current_index.column)
            elif sel_mod.current_index.column < 0:
                parent.editVerticalHeader(sel_mod.current_index.row)
            else:
                self._edit_current()

            return None

        elif keys == "F3":
            editor = QCellLabelEdit.from_table(self)
            editor.show()
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
            keys.has_shift() or self._mouse_track.last_rightclick_pos is not None
        )
        return super().keyReleaseEvent(a0)

    def inputMethodEvent(self, event: QtGui.QInputMethodEvent) -> None:
        """Catch Japanese/Chinese edit event."""
        # NOTE: super().inputMethodEvent(event) is buggy!!
        if event.preeditString():
            self._edit_current()
            # FIXME: Cannot send the pre-edit text to the editor.
            # editor.inputMethodQuery(Qt.InputMethodQuery.ImSurroundingText)

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

        # Zoom section size of headers
        self.setSectionSize(int(self._w_default * value), int(self._h_default * value))

        # Update stuff
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
        return self._selection_color

    def _set_selection_color(self, value: QtGui.QColor):
        self._selection_color = value
        self.update()

    selectionColor = Property(QtGui.QColor, _get_selection_color, _set_selection_color)

    def _get_highlight_color(self):
        return self._highlight_color

    def _set_highlight_color(self, value: QtGui.QColor):
        self._highlight_color = value
        self.update()

    highlightColor = Property(QtGui.QColor, _get_highlight_color, _set_highlight_color)

    def _get_current_index_color(self):
        return CUR_COLOR

    def paintEvent(self, event: QtGui.QPaintEvent):
        """Paint table and the selection."""
        super().paintEvent(event)
        focused = int(self.hasFocus())
        nsel = len(self._selection_model)
        painter = QtGui.QPainter(self.viewport())

        # draw highlights
        h_color = self._get_highlight_color()
        for i, rect in enumerate(
            self._rect_from_ranges(self._highlight_model._ranges, map=True)
        ):
            painter.fillRect(rect, h_color)

        # draw selections
        s_color = self._get_selection_color()
        for i, rect in enumerate(self._rect_from_ranges(self._selection_model._ranges)):
            last_one = nsel == i + 1
            pen = QtGui.QPen(s_color, 2 + int(last_one) * focused)
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

        # in-cell slot source ranges of the current index
        color_cycle = _color_cycle()
        if rng := self._current_drawing_slot_ranges:
            for rect in self._rect_from_ranges(rng.iter_ranges(), map=True):
                rect.adjust(1, 1, -1, -1)
                pen = QtGui.QPen(next(color_cycle), 3)
                painter.setPen(pen)
                painter.drawRect(rect)

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

    def parentViewer(self) -> _QtMainWidgetBase | None:
        """The parent table viewer widget."""
        parent = self.parentTable()
        return parent.parentViewer()

    def _rect_from_ranges(
        self,
        ranges: Iterable[tuple[slice, slice]],
        map: bool = False,
    ) -> Iterator[QtCore.QRect]:
        """Convert range models into rectangles."""
        model = self.model()
        prx = self.parentTable()._proxy
        for rr, cc in ranges:
            if map:
                # can only draw single-row selections during unordered state
                try:
                    rr = prx.map_slice(rr)
                except Exception:
                    continue
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


def _color_cycle() -> Iterator[QtGui.QColor]:
    """Generate easily distinguishable colors."""
    # This is the default color cycle of matplotlib
    colors = [
        QtGui.QColor(31, 119, 180),
        QtGui.QColor(255, 127, 14),
        QtGui.QColor(44, 160, 44),
        QtGui.QColor(214, 39, 40),
        QtGui.QColor(148, 103, 189),
        QtGui.QColor(140, 86, 75),
        QtGui.QColor(227, 119, 194),
        QtGui.QColor(127, 127, 127),
        QtGui.QColor(188, 189, 34),
        QtGui.QColor(23, 190, 207),
    ]
    ncolor = len(colors)
    i = 0
    while True:
        yield colors[i]
        i = i + 1 if i < ncolor - 1 else 0
