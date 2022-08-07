from __future__ import annotations
from typing import TYPE_CHECKING

from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt


class QInnerWidget(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget = None) -> None:
        super().__init__(parent)
        self._layout = QtW.QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def sizeHint(self):
        h = 0
        w = self.width()
        for child in self._layout.children():
            h += child.minimumHeight()
            w = min(w, child.minimumWidth())
        return QtCore.QSize(w, h)

    if TYPE_CHECKING:

        def layout(self) -> QtW.QVBoxLayout:
            ...


class QTableSideArea(QtW.QScrollArea):
    """The side scroll area of a table."""

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        widget_inside = QInnerWidget(self)
        self.setMinimumWidth(180)
        self.setWidget(widget_inside)

    if TYPE_CHECKING:

        def widget(self) -> QInnerWidget:
            ...

    def addWidget(self, widget: QtW.QWidget) -> None:
        self.widget().layout().addWidget(widget)

    def insertWidget(self, index: int, widget: QtW.QWidget) -> None:
        self.widget().layout().insertWidget(index, widget)

    def removeWidget(self, widget: QtW.QWidget) -> None:
        self.widget().layout().removeWidget(widget)
        if self.widget().layout().count() == 0:
            self.parentWidget().setSizes([1, 0])
