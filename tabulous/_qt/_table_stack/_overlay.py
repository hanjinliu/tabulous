from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum
from qtpy import QtWidgets as QtW, QtCore, QtGui
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


class _QOverlayBase(QtW.QDialog):

    _Style = """
    _QOverlayBase {{
        border: 1px solid gray;
        border-radius: 3px;
        background-color: {backgroundcolor};
    }}
    """

    def __init__(
        self,
        parent: QtW.QWidget | None = None,
        flags=Qt.WindowType.SubWindow,
    ) -> None:
        super().__init__(parent, flags)


class QOverlayWidget(_QOverlayBase):
    """The overlay widget appears at the fixed position."""

    def __init__(self, parent: QTabbedTableStack, duration: int = 50):
        """
        The overlay widget appears at the fixed position.

        Parameters
        ----------
        parent : QTabbedTableStack
            Parent table stack
        duration : int, default is 50
            Animation duration in msec.
        """
        super().__init__(parent)
        self._widget = None

        titlebar = QTitleBar("", self)
        titlebar.closeSignal.connect(self.hide)
        self._title_bar = titlebar
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(2, 2, 2, 2)
        _layout.setSpacing(0)
        _layout.addWidget(titlebar)

        self.setLayout(_layout)

        parent.resizedSignal.connect(self.alignToParent)
        self.setAnchor(Anchor.bottom_right)
        self.setVisible(False)

        effect = QtW.QGraphicsOpacityEffect(self)
        effect.setOpacity(0.9)
        self.setGraphicsEffect(effect)
        self._effect = effect
        self.opacity_anim = QtCore.QPropertyAnimation(self._effect, b"opacity", self)
        self._duration = duration

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
        """Title of the overlay widget."""
        return self._title_bar.title()

    def setTitle(self, title: str) -> None:
        """Set the title of the overlay widget."""
        return self._title_bar.setTitle(title)

    def hideLater(self, sec: float = 5):
        """Hide overlay widget after a delay."""
        return QtCore.QTimer.singleShot(int(sec * 1000), self._hide)

    def _hide(self):
        if self.isVisible():
            self.setVisible(False)
        return None

    # fmt: off
    if TYPE_CHECKING:
        def parentWidget(self) -> QTabbedTableStack: ...
    # fmt: on

    def show(self):
        """Show the overlay widget with animation."""
        super().show()
        self.alignToParent()
        if self.parentWidget().parent()._white_background:
            bgcolor = "white"
        else:
            bgcolor = "black"
        self.setStyleSheet(self._Style.format(backgroundcolor=bgcolor))
        self.opacity_anim.setDuration(self._duration)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(0.9)
        self.opacity_anim.start()
        return None

    def hide(self) -> None:
        """Hide the overlay widget with animation."""
        self.parentWidget().parent().setCellFocus()
        self.opacity_anim.setDuration(self._duration)
        self.opacity_anim.setStartValue(0.9)
        self.opacity_anim.setEndValue(0)
        self.opacity_anim.start()

        @self.opacity_anim.finished.connect
        def _on_vanished():
            if self.isVisible():
                self.setVisible(False)
            self.opacity_anim.finished.disconnect()

        return None

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


class QOverlayFrame(_QOverlayBase):

    _Style = """
    QOverlayFrame {{
        border: 1px solid gray;
        background-color: {backgroundcolor};
    }}
    """

    def __init__(self, content: QtW.QWidget, viewport: QtW.QWidget):
        super().__init__(viewport)
        self.setLayout(QtW.QVBoxLayout())

        content.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self.layout().addWidget(content)
        self.layout().setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().setContentsMargins(0, 0, 0, 0)

        sizegrip = QtW.QSizeGrip(self)
        self._label_widget = QtW.QLabel()

        _footer = QtW.QWidget()
        _footer.setLayout(QtW.QHBoxLayout())
        _footer.layout().addWidget(
            self._label_widget, False, Qt.AlignmentFlag.AlignLeft
        )
        _footer.layout().addWidget(
            sizegrip, False, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom
        )
        _footer.setContentsMargins(0, 0, 0, 0)
        _footer.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Minimum
        )
        self.layout().addWidget(_footer)

    def label(self) -> str:
        return self._label_widget.text()

    def setLabel(self, label: str) -> None:
        return self._label_widget.setText(label)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag_start = event.pos()
        return None

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._drag_start = None
        return None

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._drag_start is not None:
            self.move(self.mapToParent(event.pos() - self._drag_start))
        return None

    def tableStack(self) -> QTabbedTableStack:
        qtable = self.parent().parent().parent()
        return qtable.tableStack()

    def show(self):
        """Show the overlay widget."""
        super().show()
        if self.tableStack().parent()._white_background:
            bgcolor = "white"
        else:
            bgcolor = "black"
        self.setStyleSheet(self._Style.format(backgroundcolor=bgcolor))
        return None
