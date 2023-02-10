from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui, QtCore


class QTitleLabel(QtW.QLabel):
    """Label used for titles in the preference dialog."""

    def __init__(self, text: str, size: int) -> None:
        super().__init__()
        self.setText(text)
        self.setFont(QtGui.QFont("Arial", size))

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        color = self.palette().color(QtGui.QPalette.ColorRole.Foreground)
        painter.setPen(QtGui.QPen(color, 1))
        bottom_left = self.rect().bottomLeft()
        bottom_right = QtCore.QPoint(bottom_left.x() + 300, bottom_left.y())
        painter.drawLine(bottom_left, bottom_right)
        return super().paintEvent(a0)
