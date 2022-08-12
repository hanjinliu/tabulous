from __future__ import annotations
from typing import TYPE_CHECKING

from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt


class QInnerSplitter(QtW.QSplitter):
    def __init__(self, parent: QtW.QWidget = None) -> None:
        super().__init__(Qt.Orientation.Vertical, parent)

    def sizeHint(self):
        h = 0
        w = self.width()
        nwidgets = self.count()
        for i in range(nwidgets):
            child = self.widget(i)
            h += child.minimumHeight()
            w = min(w, child.minimumWidth())
        return QtCore.QSize(w, h)


class QTableSideArea(QtW.QScrollArea):
    """The side scroll area of a table."""

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        widget_inside = QInnerSplitter(self)
        self.setMinimumWidth(180)
        self.setWidget(widget_inside)

    if TYPE_CHECKING:

        def widget(self) -> QInnerSplitter:
            ...

    def addWidget(self, widget: QtW.QWidget) -> None:
        dock = QSplitterDockWidget(widget)
        splitter = self.widget()
        splitter.addWidget(dock)
        idx = splitter.count() - 1
        splitter.setCollapsible(idx, False)

        @dock.close_btn.clicked.connect
        def _():
            self.removeWidget(dock)

    def removeWidget(self, widget: QtW.QWidget) -> None:
        widget.setParent(None)
        if self.widget().count() == 0:
            self.parentWidget().setSizes([1, 0])


class QTitleBar(QtW.QWidget):
    """A custom title bar for a QSplitterDockWidget"""

    def __init__(self, parent: QSplitterDockWidget) -> None:
        super().__init__(parent)
        _layout = QtW.QHBoxLayout()
        _layout.setContentsMargins(4, 0, 4, 0)
        _layout.setSpacing(0)
        _frame = QtW.QFrame()
        _frame.setFrameShape(QtW.QFrame.Shape.HLine)
        _frame.setFrameShadow(QtW.QFrame.Shadow.Sunken)
        _frame.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )
        self._close_button = QtW.QPushButton("✕")
        self._close_button.setToolTip("Close the widget.")
        self._close_button.setFixedSize(QtCore.QSize(16, 16))

        _layout.addWidget(_frame)
        _layout.addWidget(self._close_button)
        _layout.setAlignment(self._close_button, Qt.AlignmentFlag.AlignRight)
        self.setLayout(_layout)
        self.setMaximumHeight(20)


class QSplitterDockWidget(QtW.QWidget):
    def __init__(self, widget: QtW.QWidget) -> None:
        super().__init__()
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(0, 0, 0, 0)
        _layout.setSpacing(0)
        title = QTitleBar(self)
        _layout.addWidget(title)
        _layout.addWidget(widget)
        self.setLayout(_layout)

        self._title_bar = title
        self._widget = widget

    @property
    def close_btn(self):
        return self._title_bar._close_button
