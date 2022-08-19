from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal
import pandas as pd

if TYPE_CHECKING:
    from ._enhanced_table import _QTableViewEnhanced


class QDataFrameHeaderView(QtW.QHeaderView):
    _Orientation: Qt.Orientation
    selectionChangedSignal = Signal(int, int)

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(self._Orientation, parent)
        self._index_start = None
        self._index_stop = None
        self.setSelectionMode(QtW.QHeaderView.SelectionMode.SingleSelection)

    # fmt: off
    if TYPE_CHECKING:
        def parentWidget(self) -> _QTableViewEnhanced: ...
    # fmt: on

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        self._index_start = self._index_stop = self.logicalIndexAt(e.pos())
        _selection_model = self.parentWidget()._selection_model
        if not _selection_model._ctrl_on:
            _selection_model.clear()
        _selection_model._selections.append((slice(0, 0), slice(0, 0)))  # temporary
        self.selectionChangedSignal.emit(self._index_start, self._index_stop)
        return super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        if self._index_start is None:
            return super().mouseMoveEvent(e)
        pos = self.logicalIndexAt(e.pos())
        if self._index_stop != pos:
            self._index_stop = pos
            self.selectionChangedSignal.emit(self._index_start, self._index_stop)
        return super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        self._index_start = None
        return super().mouseReleaseEvent(e)


class QHorizontalHeaderView(QDataFrameHeaderView):
    _Orientation = Qt.Orientation.Horizontal


class QVerticalHeaderView(QDataFrameHeaderView):
    _Orientation = Qt.Orientation.Vertical
