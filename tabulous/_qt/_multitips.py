from __future__ import annotations
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt


class _QHasToolTip(QtW.QWidget):
    _labels: list[QKeyComboTip] = []

    def toolTipPosition(self, index: int) -> QtCore.QPoint:
        """Return the position of the tooltip for the given index."""
        raise NotImplementedError()

    def toolTipText(self, index: int) -> str:
        """Return the text of the tooltip for the given index."""
        return str(index)

    def toolTipNumber(self) -> int:
        """Return the number of tooltips."""
        raise NotImplementedError()

    def showTabTooltips(self):
        """Show all the tooltips."""
        self._labels = []
        for i in range(self.toolTipNumber()):
            label = QKeyComboTip(self.toolTipText(i), self)
            pos = self.toolTipPosition(i)
            label.move(self.mapToGlobal(pos))
            label.show()
            self._labels.append(label)

    def hideTabTooltips(self):
        """Hide all the tooltips."""
        for label in self._labels:
            label.hide()
        self._labels = []


class QKeyComboTip(QtW.QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent, Qt.WindowType.ToolTip)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.font()
        font.setPointSize(14)
        self.setFont(font)
        self.setFixedSize(20, 20)
        self.setStyleSheet("border: 1px solid gray;")
        self.hide()
