from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt

if TYPE_CHECKING:
    from ..._table_stack import QTabbedTableStack


class QOverlayFrame(QtW.QDialog):
    """The overlay frame widget used to display the overlaid widget in tables."""

    _Style = """
    QOverlayFrame {{
        border: 1px solid gray;
        background-color: {backgroundcolor};
    }}
    """

    def __init__(self, content: QtW.QWidget, viewport: QtW.QWidget):
        super().__init__(viewport, Qt.WindowType.SubWindow)

        self.setLayout(QtW.QVBoxLayout())

        content.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )

        self.layout().addWidget(
            QtW.QSizeGrip(self),
            False,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )

        self.layout().addWidget(content)
        self.layout().setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().setContentsMargins(0, 0, 0, 0)

        self._label_widget = QtW.QLabel()
        self._label_widget.setContentsMargins(5, 2, 5, 2)

        _footer = QtW.QWidget()
        _footer.setLayout(QtW.QHBoxLayout())
        _footer.layout().addWidget(
            self._label_widget, False, Qt.AlignmentFlag.AlignLeft
        )
        _footer.layout().addWidget(
            QtW.QSizeGrip(self),
            False,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )
        _footer.setContentsMargins(0, 0, 0, 0)
        _footer.layout().setContentsMargins(0, 0, 0, 0)
        _footer.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Minimum
        )
        self.layout().addWidget(_footer)

        effect = QtW.QGraphicsDropShadowEffect(self, blurRadius=5, xOffset=2, yOffset=3)
        effect.setColor(QtGui.QColor(128, 128, 128, 72))
        self.setGraphicsEffect(effect)

    def label(self) -> str:
        return self._label_widget.text()

    def setLabel(self, label: str) -> None:
        return self._label_widget.setText(label)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag_start = event.pos()
        self.raise_()
        self.setFocus()
        return None

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._drag_start = None
        return None

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == Qt.Key.Key_Escape:
            # by default, this will close the overlay
            a0.ignore()
            return None
        return super().keyPressEvent(a0)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._drag_start is not None:
            self.move(self.mapToParent(event.pos() - self._drag_start))
        return None

    def tableStack(self) -> QTabbedTableStack:
        """The parent table stack."""
        return self.parent().parent().parent().tableStack()

    def show(self):
        """Show the overlay widget."""
        super().show()
        if self.tableStack().parent()._white_background:
            bgcolor = "white"
        else:
            bgcolor = "black"
        self.setStyleSheet(self._Style.format(backgroundcolor=bgcolor))
        return None
