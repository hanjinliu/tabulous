from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Signal, Qt

if TYPE_CHECKING:
    from ._tabwidget import QTabbedTableStack


class Anchor(Enum):
    """Anchor position"""

    top_left = "top_left"
    top_right = "top_right"
    bottom_left = "bottom_left"
    bottom_right = "bottom_right"


class QOverlayWidget(QtW.QDialog):
    def __init__(self, parent: QTabbedTableStack):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow)
        self._widget = None

        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(2, 2, 2, 2)
        _layout.setSpacing(0)

        self.setLayout(_layout)

        parent.resizedSignal.connect(self.alignToParent)
        self.setAnchor(Anchor.bottom_right)
        self.hide()

    def addWidget(self, widget: QtW.QWidget):
        if self.layout().count() > 0:
            self.removeWidget()
        self.layout().addWidget(widget)
        self.resize(widget.sizeHint())
        self._widget = widget
        self.alignToParent()

    def removeWidget(self):
        self._widget = None
        self.layout().removeWidget(self.layout().itemAt(0).widget())
        self.resize(QtCore.QSize(0, 0))

    def widget(self) -> QtW.QWidget:
        return self._widget

    def anchor(self) -> Anchor:
        return self._anchor

    def setAnchor(self, anc: Anchor | str) -> None:
        self._anchor = Anchor(anc)
        return self.alignToParent()

    if TYPE_CHECKING:

        def parentWidget(self) -> QTabbedTableStack:
            ...

    def show(self):
        super().show()
        return self.alignToParent()

    def sizeHint(self) -> QtCore.QSize:
        return super().sizeHint()

    def alignToParent(self, offset=(8, 8)):
        """Position widget at the bottom right edge of the parent."""
        qtable = self.parentWidget()
        if not qtable:
            return
        if self._anchor == Anchor.bottom_left:
            self.alignBottomLeft(offset)
        elif self._anchor == Anchor.bottom_right:
            self.alignBottomRight(offset)
        elif self._anchor == Anchor.top_left:
            self.alignTopLeft(offset)
        elif self._anchor == Anchor.top_right:
            self.alignTopRight(offset)
        else:
            raise RuntimeError

    def viewRect(self) -> QtCore.QRect:
        """Return the parent table rect."""
        parent = self.parentWidget()
        rect = parent.rect()
        return rect

    def alignTopLeft(self, offset=(8, 8)):
        pos = self.viewRect().topLeft()
        pos.setX(pos.x() + offset[0])
        pos.setY(pos.y() + offset[1])
        self.move(pos)

    def alignTopRight(self, offset=(8, 8)):
        pos = self.viewRect().topRight()
        pos.setX(pos.x() - self.rect().width() - offset[0])
        pos.setY(pos.y() + offset[1])
        self.move(pos)

    def alignBottomLeft(self, offset=(8, 8)):
        pos = self.viewRect().bottomLeft()
        pos.setX(pos.x() + offset[0])
        pos.setY(pos.y() - self.rect().height() - offset[1])
        self.move(pos)

    def alignBottomRight(self, offset=(8, 8)):
        pos = self.viewRect().bottomRight()
        pos.setX(pos.x() - self.rect().width() - offset[0])
        pos.setY(pos.y() - self.rect().height() - offset[1])
        self.move(pos)
