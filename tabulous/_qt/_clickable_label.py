from __future__ import annotations
from typing import Callable
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal


class QClickableLabel(QtW.QLabel):
    """A label widget that behaves like a button."""

    clicked = Signal()

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setFont(QtGui.QFont("Arial"))
        self.setFixedHeight(24)

        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Expanding
        )
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setStyleSheet("QClickableLabel { color: #319DFF; }")
        self.setText(text)
        self._tooltip_func = lambda: ""
        self.setToolTipDuration(200)
        return None

    def setText(self, text: str):
        fm = QtGui.QFontMetrics(self.font())
        width = fm.width(text)
        self.setFixedWidth(width + 18)
        return super().setText(text)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        return super().mouseReleaseEvent(ev)

    def enterEvent(self, a0: QtCore.QEvent) -> None:
        font = self.font()
        font.setUnderline(True)
        self.setFont(font)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()
        return super().enterEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        font = self.font()
        font.setUnderline(False)
        self.setFont(font)
        self.unsetCursor()
        return super().leaveEvent(a0)

    def setTooltipFunction(self, f: Callable[[], str]) -> None:
        self._tooltip_func = f
        return None

    def event(self, event: QtCore.QEvent):
        tp = event.type()
        if tp == QtCore.QEvent.Type.ToolTip:
            tooltip = self._tooltip_func()
            QtW.QToolTip.showText(QtGui.QCursor.pos(), tooltip, self)
            return True
        else:
            return super().event(event)
