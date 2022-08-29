from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore
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
        self._index_start = self._index_stop = logicalIndex
        _selection_model = self.parentWidget()._selection_model
        if not _selection_model._ctrl_on:
            _selection_model.clear()
        self.parentWidget()._selection_model.add_dummy()
        self.selectionChangedSignal.emit(self._index_start, self._index_stop)
        return None

    def _on_section_entered(self, logicalIndex: int) -> None:
        if self._index_start is None:
            return None
        self._index_stop = logicalIndex
        self.selectionChangedSignal.emit(self._index_start, self._index_stop)
        return None

    def _on_section_clicked(self, logicalIndex) -> None:
        self._index_start = None

    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        index = self.logicalIndexAt(pos)
        return self.execContextMenu(index)


class QHorizontalHeaderView(QDataFrameHeaderView):
    _Orientation = Qt.Orientation.Horizontal


class QVerticalHeaderView(QDataFrameHeaderView):
    _Orientation = Qt.Orientation.Vertical
