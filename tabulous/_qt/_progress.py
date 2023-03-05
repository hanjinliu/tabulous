from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Property, Signal
from enum import Enum


class ButtonState(Enum):
    NONE = "none"
    SQUARE = "square"
    TRIANGLE = "triangle"


class QCircularProgressBar(QtW.QWidget):
    abortRequested = Signal()
    infiniteRequested = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._value = 0
        self._minimum = 0
        self._maximum = 100
        self._timer = QtCore.QTimer(self)
        self._radius = 20
        self._barWidth = 4
        self._infinite = False
        self._pen = QtGui.QPen(
            QtGui.QColor(0, 48, 48, 255),
            self._barWidth,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
        self._groove_pen = QtGui.QPen(
            QtGui.QColor(230, 230, 230, 255),
            self._barWidth,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
        self._btn_state = ButtonState.NONE
        self.setMouseTracking(True)
        self.infiniteRequested.connect(self.setInfinite)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(self._radius * 2, self._radius * 2)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
        center = self.rect().center()
        x0 = center.x() - self._radius
        y0 = center.y() - self._radius
        rect = QtCore.QRect(x0, y0, 2 * self._radius, 2 * self._radius)
        ratio = self._value / self._maximum
        min_ratio = self._minimum / self._maximum
        _full = 360 * 16
        painter.setPen(self._groove_pen)
        painter.drawArc(rect, 0, _full)
        painter.setPen(self._pen)
        painter.drawArc(rect, 90 * 16 - int(_full * min_ratio), -int(_full * ratio))

        if self._btn_state is ButtonState.SQUARE:
            _l = self._radius * 0.4
            x0 = center.x() - _l
            y0 = center.y() - _l
            rect = QtCore.QRectF(x0, y0, 2 * _l, 2 * _l)
            painter.setPen(QtGui.QPen(self._pen.color(), 1))
            painter.setBrush(QtGui.QBrush(self._pen.color()))
            painter.drawRect(rect)
        elif self._btn_state is ButtonState.TRIANGLE:
            path = QtGui.QPainterPath()
            _l = self._radius * 0.6
            path.moveTo(center.x() - _l / 2, center.y() + _l * 0.866)
            path.lineTo(center.x() - _l / 2, center.y() - _l * 0.866)
            path.lineTo(center.x() + _l, center.y())
            path.lineTo(center.x() - _l / 2, center.y() + _l * 0.866)
            painter.fillPath(path, QtGui.QBrush(self._pen.color()))

    def value(self) -> float:
        return self._value

    def setValue(self, value: float) -> None:
        if value < 0:
            self.infiniteRequested.emit(True)
        else:
            self.infiniteRequested.emit(False)
            self._value = value
            self.update()

    @Property(QtGui.QColor)
    def grooveColor(self) -> QtGui.QColor:
        return self._groove_pen.color()

    @grooveColor.setter
    def grooveColor(self, color: QtGui.QColor) -> None:
        self._groove_pen.setColor(color)
        self.update()

    @Property(QtGui.QColor)
    def color(self) -> QtGui.QColor:
        return self._pen.color()

    @color.setter
    def color(self, color: QtGui.QColor) -> None:
        self._pen.setColor(color)
        self.update()

    def buttonState(self) -> ButtonState:
        return self._btn_state

    def setButtonState(self, state: ButtonState) -> None:
        self._btn_state = ButtonState(state)
        self.update()

    def _is_inside(self, pos: QtCore.QPoint) -> bool:
        center = self.rect().center()
        dist = (center.x() - pos.x()) ** 2 + (center.y() - pos.y()) ** 2
        return dist < self._radius**2

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._is_inside(event.pos()):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_inside(event.pos()):
            self.abortRequested.emit()

    def setInfinite(self, infinite: bool) -> None:
        if infinite and not self._infinite:
            self._timer.setInterval(15)
            self._timer.timeout.connect(self._on_infinite_timeout)
            self._timer.start()
            self._minimum = 0
            self._value = 25
        elif not infinite and self._infinite:
            self._timer.stop()
            self._value = 0
            self._minimum = 0
        self._infinite = infinite
        self.update()

    def _on_infinite_timeout(self):
        self._minimum = (self._minimum + 1) % self._maximum
        self.update()

    def radius(self) -> float:
        """Radius of the progress bar in pixels"""
        return self._radius

    def setRadius(self, radius: float) -> None:
        """Set radius of the progress bar in pixels"""
        self._radius = radius
        self.update()

    def barWidth(self) -> float:
        return self._barWidth

    def setBarWidth(self, width: float) -> None:
        """Set width of the progress bar in pixels"""
        self._barWidth = width
        self._pen.setWidth(width)
        self._groove_pen.setWidth(width)
        self.update()
