from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal

from ..._action_registry import QActionRegistry

if TYPE_CHECKING:
    from ._enhanced_table import _QTableViewEnhanced


class QDataFrameHeaderView(QtW.QHeaderView, QActionRegistry[int]):
    """The header view for the tabulous tables."""

    _Orientation: Qt.Orientation
    selectionChangedSignal = Signal(int, int)

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        QtW.QHeaderView.__init__(self, self._Orientation, parent)
        QActionRegistry.__init__(self)
        self._index_start = None
        self._index_stop = None
        self._index_current = None
        self._selected_ranges: list[slice] = []
        self.setSelectionMode(QtW.QHeaderView.SelectionMode.SingleSelection)
        self.setSectionsClickable(True)
        self.sectionPressed.connect(self._on_section_pressed)  # pressed
        self.sectionClicked.connect(self._on_section_clicked)  # released
        self.sectionEntered.connect(self._on_section_entered)  # dragged

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    # fmt: off
    if TYPE_CHECKING:
        def parentWidget(self) -> _QTableViewEnhanced: ...
    # fmt: on

    def _on_section_pressed(self, logicalIndex: int) -> None:
        ctrl_on = self._is_ctrl_on()
        self._reset_others(ctrl_on)
        self._index_start = self._index_stop = self._index_current = logicalIndex
        _selection_model = self.parentWidget()._selection_model
        if not ctrl_on:
            _selection_model.clear()
            self._selected_ranges.clear()
        _selection_model.add_dummy()
        self._selected_ranges.append(slice(self._index_start, self._index_stop + 1))
        self.selectionChangedSignal.emit(self._index_start, self._index_stop)
        self.update()
        self.viewport().update()
        return None

    def _on_section_entered(self, logicalIndex: int) -> None:
        if self._index_start is None:
            return None
        self._index_stop = self._index_current = logicalIndex
        self._selected_ranges[-1] = slice(self._index_start, self._index_stop + 1)
        self.selectionChangedSignal.emit(self._index_start, self._index_stop)
        self.update()
        return None

    def _on_section_clicked(self, logicalIndex) -> None:
        self._index_start = None
        self.update()

    def _is_ctrl_on(self) -> bool:
        return self.parentWidget()._selection_model._ctrl_on

    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        index = self.logicalIndexAt(pos)
        return self.execContextMenu(index)

    def _reset_selections(self) -> None:
        self._index_current = None
        self._selected_ranges.clear()

    def _reset_others(self, ctrl_on: bool) -> None:
        """This method should be defined in the child class."""

    def visualRectAtIndex(self, index: int) -> QtCore.QRect:
        """Return the visual rect of the given index."""
        raise NotImplementedError()

    def drawBorder(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        """Draw the opened border of a section."""
        raise NotImplementedError()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self.viewport())
        pen = QtGui.QPen(Qt.GlobalColor.darkBlue, 3)
        painter.setPen(pen)
        for _slice in self._selected_ranges:
            rect_start = self.visualRectAtIndex(_slice.start)
            rect_stop = self.visualRectAtIndex(_slice.stop - 1)
            rect = rect_start | rect_stop
            self.drawBorder(painter, rect)
        return None


class QHorizontalHeaderView(QDataFrameHeaderView):
    _Orientation = Qt.Orientation.Horizontal

    def _reset_others(self, ctrl_on: bool) -> None:
        vheader = self.parentWidget().verticalHeader()
        vheader._index_current = None
        if not ctrl_on:
            vheader._selected_ranges.clear()
        vheader.update()
        vheader.viewport().update()
        return None

    def visualRectAtIndex(self, index: int) -> QtCore.QRect:
        x = self.sectionViewportPosition(index)
        y = self.rect().top()
        height = self.height()
        width = self.sectionSize(index)
        return QtCore.QRect(x, y, width, height)

    def drawBorder(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        painter.drawPolyline(
            rect.bottomLeft(),
            rect.topLeft(),
            rect.topRight(),
            rect.bottomRight(),
        )


class QVerticalHeaderView(QDataFrameHeaderView):
    _Orientation = Qt.Orientation.Vertical

    def _reset_others(self, ctrl_on: bool) -> None:
        hheader = self.parentWidget().horizontalHeader()
        hheader._index_current = None
        if not ctrl_on:
            hheader._selected_ranges.clear()
        hheader.update()
        hheader.viewport().update()
        return None

    def visualRectAtIndex(self, index: int) -> QtCore.QRect:
        x = self.rect().left()
        y = self.sectionViewportPosition(index)
        height = self.sectionSize(index)
        width = self.width()
        return QtCore.QRect(x, y, width, height)

    def drawBorder(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        painter.drawPolyline(
            rect.topRight(),
            rect.topLeft(),
            rect.bottomLeft(),
            rect.bottomRight(),
        )
