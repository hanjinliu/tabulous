from __future__ import annotations
from typing import TYPE_CHECKING, Iterator, cast
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal

import numpy as np

from tabulous._qt._action_registry import QActionRegistry
from tabulous._qt._proxy_button import HeaderAnchorMixin

if TYPE_CHECKING:
    from ._enhanced_table import _QTableViewEnhanced


class QDataFrameHeaderView(QtW.QHeaderView, QActionRegistry[int]):
    """The header view for the tabulous tables."""

    _Orientation: Qt.Orientation
    selectionChangedSignal = Signal(int, int)

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        QtW.QHeaderView.__init__(self, self._Orientation, parent)
        QActionRegistry.__init__(self)
        self.setSelectionMode(QtW.QHeaderView.SelectionMode.SingleSelection)
        self.setSectionsClickable(True)
        self.sectionPressed.connect(self._on_section_pressed)  # pressed
        self.sectionClicked.connect(self._on_section_clicked)  # released
        self.sectionEntered.connect(self._on_section_entered)  # dragged
        self.sectionResized.connect(self._on_section_resized)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._section_sizes = np.zeros(0, dtype=np.float32)
        self._header_widgets: dict[int, QtW.QWidget] = {}

    # fmt: off
    if TYPE_CHECKING:
        def parentWidget(self) -> _QTableViewEnhanced: ...
    # fmt: on

    @property
    def selection_model(self):
        return self.parentWidget()._selection_model

    def _on_section_pressed(self, logicalIndex: int) -> None:
        self.selection_model.jump_to(*self._index_for_selection_model(logicalIndex))
        self.selection_model.set_shift(True)
        return None

    def _on_section_entered(self, logicalIndex: int) -> None:
        self.selection_model.move_to(*self._index_for_selection_model(logicalIndex))
        return None

    def _on_section_clicked(self, logicalIndex) -> None:
        self.selection_model.set_shift(False)

    def _on_section_resized(
        self, logicalIndex: int, oldSize: int, newSize: int
    ) -> None:
        self._section_sizes[logicalIndex] = newSize
        for idx, widget in self._header_widgets.items():
            if idx < logicalIndex:
                continue
            widget.move(widget.x() + newSize - oldSize, widget.y())

    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        index = self.logicalIndexAt(pos)
        # press header if it is not selected.
        for sel in self._iter_selections():
            if sel.start <= index < sel.stop:
                break
        else:
            self._on_section_pressed(index)
        return self.execContextMenu(self.viewport().mapToGlobal(pos), index)

    def _iter_selections(self) -> Iterator[slice]:
        """Iterate selections"""
        raise NotImplementedError()

    def _index_for_selection_model(self, logicalIndex: int) -> tuple[int, int]:
        raise NotImplementedError()

    def visualRectAtIndex(self, index: int) -> QtCore.QRect:
        """Return the visual rect of the given index."""
        raise NotImplementedError()

    @staticmethod
    def drawBorder(painter: QtGui.QPainter, rect: QtCore.QRect):
        """Draw the opened border of a section."""
        raise NotImplementedError()

    def drawCurrent(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        """Draw the current index if exists."""
        raise NotImplementedError()

    def setZoomRatio(self, ratio: float):
        self._section_sizes *= ratio
        self.sectionResized.disconnect(self._on_section_resized)
        try:
            for idx, size in enumerate(self._section_sizes):
                self.resizeSection(idx, size)
        finally:
            self.sectionResized.connect(self._on_section_resized)
        return None

    def insertSection(self, index: int, count: int, span: int = 0) -> None:
        """Insert a section at the given index."""
        sz = self._section_sizes
        self._section_sizes = np.concatenate(
            [sz[:index], np.full(count, span), sz[index:]]
        )
        return None

    def removeSection(self, index: int, count: int) -> None:
        """Remove the section at the given index."""
        self._section_sizes = np.delete(
            self._section_sizes, slice(index, index + count)
        )
        return None

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self.viewport())
        color = self.parentWidget()._get_selection_color()
        pen = QtGui.QPen(color, 3)
        painter.setPen(pen)

        # paint selections
        for _slice in self._iter_selections():
            rect_start = self.visualRectAtIndex(_slice.start)
            rect_stop = self.visualRectAtIndex(_slice.stop - 1)
            rect = rect_start | rect_stop
            self.drawBorder(painter, rect)

        # paint current
        self.drawCurrent(painter)
        return None

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        if editor := self.parentWidget()._focused_widget:
            editor.setFocus()
        return super().mouseReleaseEvent(e)

    def sectionWidget(self, idx: int) -> QtW.QWidget | None:
        """The widget anchored at the given section."""
        return self._header_widgets.get(idx, None)

    def setSectionWidget(self, idx: int, widget: QtW.QWidget) -> None:
        """Set the widget anchored at the given section."""
        if not isinstance(widget, QtW.QWidget):
            raise TypeError(f"Expected a QWidget, got {type(widget)}")
        if idx in self._header_widgets:
            self.removeSectionWidget(idx)
        self._header_widgets[idx] = widget
        widget.setParent(self.viewport())
        w, h = widget.width(), widget.height()
        rect = self.visualRectAtIndex(idx)
        rect.adjust(2, 2, -2, -2)
        rect.setLeft(rect.left() + rect.width() - w)
        rect.setTop(rect.top() + rect.height() - h)
        widget.setGeometry(rect)
        if isinstance(widget, HeaderAnchorMixin):
            _widget = cast(HeaderAnchorMixin, widget)
            _widget.on_installed(self.parentWidget().parentTable(), idx)
        widget.show()
        return None

    def removeSectionWidget(self, idx: int | None = None):
        table = self.parentWidget().parentTable()
        if idx is None:
            for idx in self._header_widgets:
                widget = self._header_widgets[idx]
                widget.hide()
                if isinstance(widget, HeaderAnchorMixin):
                    _widget = cast(HeaderAnchorMixin, widget)
                    _widget.on_uninstalled(table, idx)
                widget.setParent(None)
            self._header_widgets.clear()
        else:
            widget = self._header_widgets.pop(idx)
            widget.hide()
            if isinstance(widget, HeaderAnchorMixin):
                _widget = cast(HeaderAnchorMixin, widget)
                _widget.on_uninstalled(table, idx)
            widget.setParent(None)
        return None


class QHorizontalHeaderView(QDataFrameHeaderView):
    _Orientation = Qt.Orientation.Horizontal

    def visualRectAtIndex(self, index: int) -> QtCore.QRect:
        x = self.sectionViewportPosition(index)
        y = self.rect().top()
        height = self.height()
        width = self.sectionSize(index)
        return QtCore.QRect(x, y, width, height)

    @staticmethod
    def drawBorder(painter: QtGui.QPainter, rect: QtCore.QRect):
        return painter.drawPolyline(
            rect.bottomLeft(),
            rect.topLeft(),
            rect.topRight(),
            rect.bottomRight(),
        )

    def drawCurrent(self, painter: QtGui.QPainter):
        row, col = self.selection_model.current_index
        if row < 0 and col >= 0:
            rect_current = self.visualRectAtIndex(col)
            rect_current.adjust(1, 1, -1, -1)
            color = self.parentWidget()._get_current_index_color()
            pen = QtGui.QPen(color, 3)
            painter.setPen(pen)
            painter.drawRect(rect_current)
        return None

    def _iter_selections(self):
        yield from self.selection_model.iter_col_selections()

    def _index_for_selection_model(self, logicalIndex):
        return -1, logicalIndex


class QVerticalHeaderView(QDataFrameHeaderView):
    _Orientation = Qt.Orientation.Vertical

    def visualRectAtIndex(self, index: int) -> QtCore.QRect:
        x = self.rect().left()
        y = self.sectionViewportPosition(index)
        height = self.sectionSize(index)
        width = self.width()
        return QtCore.QRect(x, y, width, height)

    @staticmethod
    def drawBorder(painter: QtGui.QPainter, rect: QtCore.QRect):
        return painter.drawPolyline(
            rect.topRight(),
            rect.topLeft(),
            rect.bottomLeft(),
            rect.bottomRight(),
        )

    def drawCurrent(self, painter: QtGui.QPainter):
        row, col = self.selection_model.current_index
        if col < 0 and row >= 0:
            rect_current = self.visualRectAtIndex(row)
            rect_current.adjust(1, 1, -1, -1)
            color = self.parentWidget()._get_current_index_color()
            pen = QtGui.QPen(color, 4)
            painter.setPen(pen)
            painter.drawRect(rect_current)
        return None

    def _iter_selections(self):
        yield from self.selection_model.iter_row_selections()

    def _index_for_selection_model(self, logicalIndex):
        return logicalIndex, -1
