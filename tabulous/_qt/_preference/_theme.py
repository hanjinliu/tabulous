from __future__ import annotations
from functools import partial

from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal
from tabulous.style import Style, GLOBAL_STYLES
from tabulous._qt._mainwindow import QMainWindow
from tabulous._utils import get_config, update_config


class QThemePanel(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self._labels: dict[str, QThemeSelectionLabel] = {}
        _layout = QtW.QGridLayout()
        row = 0
        col = 0
        ncols = 6

        for name, style in GLOBAL_STYLES.items():
            label = QThemeSelectionLabel(style)
            label.setToolTip(name)
            self._labels[name] = label
            label.clicked.connect(partial(self.setTheme, name=name))
            _layout.addWidget(label, row, col)
            col += 1
            if col >= ncols:
                row += 1
                col = 0

        self.setLayout(_layout)
        self.setMinimumSize(200, 100)
        name = get_config().window.theme
        self._update_check_state(name)

    def setTheme(self, name: str):
        cfg = get_config()
        cfg.window.theme = name
        update_config(cfg)
        QMainWindow.reload_config()
        self._update_check_state(name)

    def _update_check_state(self, name: str):
        for key, wdt in self._labels.items():
            wdt.setChecked(key == name)


class QThemeSelectionLabel(QtW.QLabel):
    clicked = Signal()

    def __init__(self, style: Style) -> None:
        super().__init__()
        self._style_theme = style
        self.setFixedSize(30, 30)
        self.setFont(QtGui.QFont("Arial", 16))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False

    def setChecked(self, checked: bool):
        self._checked = checked
        self.update()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.clicked.emit()
        return super().mouseReleaseEvent(ev)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(30, 30)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        geo = self.rect()

        grad = QtGui.QLinearGradient(
            QtCore.QPointF(geo.topLeft()), QtCore.QPointF(geo.bottomRight())
        )
        grad.setColorAt(0, QtGui.QColor(self._style_theme.background0))
        grad.setColorAt(1, QtGui.QColor(self._style_theme.background1))
        path = QtGui.QPainterPath(QtCore.QPointF(geo.topLeft()))
        path.lineTo(QtCore.QPointF(geo.topRight()))
        path.lineTo(QtCore.QPointF(geo.bottomLeft()))
        painter.fillPath(path, grad)

        grad = QtGui.QLinearGradient(
            QtCore.QPointF(geo.topLeft()), QtCore.QPointF(geo.bottomRight())
        )
        grad.setColorAt(0, QtGui.QColor(self._style_theme.highlight0))
        grad.setColorAt(1, QtGui.QColor(self._style_theme.highlight1))
        path = QtGui.QPainterPath(QtCore.QPointF(geo.topRight()))
        path.lineTo(QtCore.QPointF(geo.bottomLeft()))
        path.lineTo(QtCore.QPointF(geo.bottomRight()))
        painter.fillPath(path, grad)

        if self._checked:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 20, 20), 3))
            painter.drawRect(geo)

        painter.setPen(QtGui.QPen(QtGui.QColor(self._style_theme.foreground), 3))
        painter.drawText(geo, Qt.AlignmentFlag.AlignCenter, "A")
        return None
