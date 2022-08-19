from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt
from .._titlebar import QTitleBar

if TYPE_CHECKING:
    from ._tabwidget import QTabbedTableStack


class Anchor(Enum):
    """Anchor position"""

    top_left = "top_left"
    top_right = "top_right"
    bottom_left = "bottom_left"
    bottom_right = "bottom_right"


class QOverlayWidget(QtW.QDialog):
    """The overlay widget appears at the fixed position."""

    def __init__(self, parent: QTabbedTableStack):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow)
        self._widget = None
        self.setStyleSheet(
            "QOverlayWidget {border: 1px solid gray; border-radius: 3px; background-color: white;}"
        )

        titlebar = QTitleBar("", self)
        titlebar.closeSignal.connect(self.hide)
        self._title_bar = titlebar
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(2, 2, 2, 2)
        _layout.addWidget(titlebar)

        self.setLayout(_layout)

        parent.resizedSignal.connect(self.alignToParent)
        self.setAnchor(Anchor.bottom_right)
        self.hide()

        effect = QtW.QGraphicsOpacityEffect(self)
        effect.setOpacity(0.9)
        self.setGraphicsEffect(effect)
        self._effect = effect

    def addWidget(self, widget: QtW.QWidget):
        """Set the central widget."""
        if self._widget is not None:
            self.removeWidget()
        self.layout().addWidget(widget)
        self.resize(widget.sizeHint() + self._title_bar.sizeHint())
        self._widget = widget
        self.alignToParent()

    def removeWidget(self):
        """Remove the central widget."""
        self._widget.setParent(None)
        self._widget = None
        self.resize(QtCore.QSize(0, 0))

    def widget(self) -> QtW.QWidget:
        """The central widget."""
        return self._widget

    def anchor(self) -> Anchor:
        """Anchor position."""
        return self._anchor

    def setAnchor(self, anc: Anchor | str) -> None:
        """Set anchor position of the overlay widget."""
        self._anchor = Anchor(anc)
        return self.alignToParent()

    def title(self) -> str:
        return self._title_bar.title()

    def setTitle(self, title: str) -> None:
        return self._title_bar.setTitle(title)

    if TYPE_CHECKING:

        def parentWidget(self) -> QTabbedTableStack:
            ...

    def show(self):
        super().show()
        return self.alignToParent()

    def alignToParent(self):
        """Position widget at the bottom right edge of the parent."""
        if not self.isVisible():
            return
        qtable = self.parentWidget()
        if not qtable or qtable.isEmpty():
            return
        if self._anchor == Anchor.bottom_left:
            self.alignBottomLeft()
        elif self._anchor == Anchor.bottom_right:
            self.alignBottomRight()
        elif self._anchor == Anchor.top_left:
            self.alignTopLeft()
        elif self._anchor == Anchor.top_right:
            self.alignTopRight()
        else:
            raise RuntimeError

    def viewRect(self) -> QtCore.QRect:
        """Return the parent table rect."""
        parent = self.parentWidget()
        qtable = parent.tableAtIndex(parent.currentIndex())
        wdt = qtable.widget(0)
        if wdt is None:
            rect = qtable.rect()
        else:
            rect = qtable.widget(0).rect()
        return rect

    def alignTopLeft(self, offset=(8, 8)):
        pos = self.viewRect().topLeft()
        pos.setX(pos.x() + offset[0])
        pos.setY(pos.y() + offset[1])
        self.move(pos)

    def alignTopRight(self, offset=(26, 8)):
        pos = self.viewRect().topRight()
        pos.setX(pos.x() - self.rect().width() - offset[0])
        pos.setY(pos.y() + offset[1])
        self.move(pos)

    def alignBottomLeft(self, offset=(8, 8)):
        pos = self.viewRect().bottomLeft()
        pos.setX(pos.x() + offset[0])
        pos.setY(pos.y() - self.rect().height() - offset[1])
        self.move(pos)

    def alignBottomRight(self, offset=(26, 8)):
        pos = self.viewRect().bottomRight()
        pos.setX(pos.x() - self.rect().width() - offset[0])
        pos.setY(pos.y() - self.rect().height() - offset[1])
        self.move(pos)
