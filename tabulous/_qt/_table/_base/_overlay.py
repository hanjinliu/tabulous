from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt

if TYPE_CHECKING:
    from ..._table_stack import QTabbedTableStack
    from .._base import QBaseTable


class QOverlayFrame(QtW.QDialog):
    """The overlay frame widget used to display the overlaid widget in tables."""

    def __init__(
        self,
        content: QtW.QWidget,
        viewport: QtW.QWidget,
        grip: bool = True,
        drag: bool = True,
    ):
        super().__init__(viewport, Qt.WindowType.SubWindow)

        self.setLayout(QtW.QVBoxLayout())

        self._label_widget = QtW.QLabel()
        self._label_widget.setContentsMargins(5, 2, 5, 2)
        self._drag_start = None

        content.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )

        if grip:
            self._add_header()

        self.layout().addWidget(content)
        self.layout().setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)

        if grip:
            self.layout().setContentsMargins(0, 0, 0, 0)
            self._add_footer()
        else:
            self.layout().setContentsMargins(2, 2, 2, 2)

        self.setDraggable(drag)

    def label(self) -> str:
        """The label of the overlay widget."""
        return self._label_widget.text()

    def setLabel(self, label: str) -> None:
        """Set the label of the overlay widget in the bottom."""
        return self._label_widget.setText(label)

    def draggable(self) -> bool:
        """Return if the overlay widget is draggable."""
        return self._draggable

    def setDraggable(self, draggable: bool) -> None:
        """Set if the overlay widget is draggable."""
        self._draggable = draggable
        if draggable:
            effect = QtW.QGraphicsDropShadowEffect(
                self, blurRadius=5, xOffset=2, yOffset=3
            )
            effect.setColor(QtGui.QColor(128, 128, 128, 72))
            self.setGraphicsEffect(effect)
        else:
            self.setGraphicsEffect(None)
        return None

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Change the z-order of the overlay widget."""
        if self._draggable:
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

    def parentTable(self) -> QBaseTable:
        return self.parent().parent().parent()

    def tableStack(self) -> QTabbedTableStack:
        """The parent table stack."""
        return self.parentTable().tableStack()

    def _add_header(self):
        self.layout().addWidget(
            QtW.QSizeGrip(self),
            False,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )

    def _add_footer(self):
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
