from __future__ import annotations
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
        return None

    def setText(self, text: str):
        """Set the label text and resize the widget to fit the text."""
        fm = QtGui.QFontMetrics(self.font())
        width = fm.width(text)
        self.setFixedWidth(width + 18)
        return super().setText(text)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        """Emit the clicked signal when the left mouse button is released."""
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        return super().mouseReleaseEvent(ev)

    def enterEvent(self, a0: QtCore.QEvent) -> None:
        """Add an underline to the text and change the cursor to a hand."""
        font = self.font()
        font.setUnderline(True)
        self.setFont(font)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()
        return super().enterEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        """Reset the text and cursor to their original state."""
        font = self.font()
        font.setUnderline(False)
        self.setFont(font)
        self.unsetCursor()
        return super().leaveEvent(a0)
