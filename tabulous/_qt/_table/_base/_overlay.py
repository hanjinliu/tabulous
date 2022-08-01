from __future__ import annotations
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Signal, Qt


OPACITY = 0.5


class QOverlayWidget(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        _layout = QtW.QVBoxLayout()

        self.setLayout(_layout)
        self.setWindowOpacity(OPACITY)
        _layout.addWidget(QtW.QLabel("Test"))
        _layout.addWidget(QtW.QLineEdit())
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

    def alignTopLeft(self):
        parent = self.parentWidget()
        pos = parent.rect().topLeft()
        self.move(pos)

    def alignTopRight(self):
        parent = self.parentWidget()
        pos = parent.rect().topRight()
        pos.setX(pos.x() - self.rect().width())
        self.move(pos)

    def alignBottomLeft(self):
        parent = self.parentWidget()
        pos = parent.rect().bottomLeft()
        pos.setY(pos.y() - self.rect().height())
        self.move(pos)

    def alignBottomRight(self):
        parent = self.parentWidget()
        pos = parent.rect().bottomRight()
        pos.setX(pos.x() - self.rect().width())
        pos.setY(pos.y() - self.rect().height())
        self.move(pos)
