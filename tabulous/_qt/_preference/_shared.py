from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui, QtCore
from tabulous._qt._qt_const import foreground_color_role


class QTitleLabel(QtW.QLabel):
    """Label used for titles in the preference dialog."""

    def __init__(self, text: str, size: int) -> None:
        super().__init__()
        self.setText(text)
        self.setFont(QtGui.QFont("Arial", size))

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        color = foreground_color_role(self.palette())
        painter.setPen(QtGui.QPen(color, 1))
        bottom_left = self.rect().bottomLeft()
        bottom_right = QtCore.QPoint(bottom_left.x() + 300, bottom_left.y())
        painter.drawLine(bottom_left, bottom_right)
        return super().paintEvent(a0)
