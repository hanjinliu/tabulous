from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal

if TYPE_CHECKING:
    from ._enhanced_table import _QTableViewEnhanced

# Wrapper widgets that can be used to wrap a QTableView


class QTableDualView(QtW.QSplitter):
    """Dual view of the same table."""

    def __init__(
        self,
        table: _QTableViewEnhanced,
        orientation=Qt.Orientation.Horizontal,
    ):
        super().__init__(orientation)
        self.setChildrenCollapsible(False)

        second = table.copy(link=True)

        self.addWidget(table)
        self.addWidget(second)
        self.setSizes([500, 500])

        self._table = table
        self._second = second

    def deleteLater(self) -> None:
        self._second._selection_model.moving.disconnect(self._second._on_moving)
        self._second._selection_model.moved.disconnect(self._second._on_moved)
        return super().deleteLater()


class QTablePopupView(QtW.QWidget):
    """Popup view widget for a table."""

    def __init__(self, table: _QTableViewEnhanced):
        super().__init__()
        self.setLayout(QtW.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(table)

        self._table = table
        self._second = table.copy(link=True)

        popup = QPopupWidget(table, self._second)
        self.popup = popup
        self.popup.closed.connect(lambda: self._second.setParent(None))

    def exec(self):
        self.popup.show()
        self.popup._widget.setFocus()

    def deleteLater(self) -> None:
        self._second._selection_model.moving.disconnect(self._second._on_moving)
        self._second._selection_model.moved.disconnect(self._second._on_moved)
        self.popup.close()
        return super().deleteLater()


class QPopupWidget(QtW.QWidget):
    closed = Signal()

    def __init__(
        self,
        widget: _QTableViewEnhanced = None,
        parent: _QTableViewEnhanced = None,
    ):
        super().__init__(parent, Qt.WindowType.Popup)
        self._widget = widget
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(4, 4, 4, 4)

        self._title = QtW.QLabel("")
        self._title.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Weight.Bold))
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _layout.addWidget(self._title)
        _layout.addWidget(widget)
        sizegrip = QtW.QSizeGrip(self)
        _layout.addWidget(sizegrip, False, Qt.AlignmentFlag.AlignRight)

        self.setLayout(_layout)
        _screen_rect = QtGui.QGuiApplication.screenAt(
            parent.mapToGlobal(parent.geometry().topLeft())
        ).geometry()
        _screen_center = _screen_rect.center()
        self.resize(int(_screen_rect.width() * 0.8), int(_screen_rect.height() * 0.8))
        self.move(_screen_center - self.rect().center())
        self._drag_start: QtCore.QPoint | None = None

    def setTitle(self, text: str):
        """Set the title of the popup."""
        return self._title.setText(text)

    def closeEvent(self, a0) -> None:
        self.closed.emit()
        return super().closeEvent(a0)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag_start = event.pos()
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._drag_start = None
        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._drag_start is not None:
            self.move(self.mapToParent(event.pos() - self._drag_start))

        return super().mouseMoveEvent(event)
