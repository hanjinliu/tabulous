from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal, Property
from magicclass._magicgui_compat import ButtonWidget
from magicgui.backends._qtpy.widgets import QBaseButtonWidget


class QToggleSwitch(QtW.QAbstractButton):
    """
    A iPhone style toggle switch.
    See https://stackoverflow.com/questions/14780517/toggle-switch-in-qt

    Properties
    ----------
    - onColor: QtGui.QColor
    - offColor: QtGui.QColor
    - handleColor: QtGui.QColor
    """

    toggled = Signal(bool)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)

        self._height = 16
        self._on_color = QtGui.QColor("#4D79C7")
        self._off_color = QtGui.QColor("#909090")
        self._handle_color = QtGui.QColor("#d5d5d5")
        self.offset = self._height / 2
        self._checked = False
        self._margin = 3
        self._anim = QtCore.QPropertyAnimation(self, b"offset", self)

        self.setFixedWidth(38)

    @Property(QtGui.QColor)
    def onColor(self):
        return self._on_color

    @onColor.setter
    def onColor(self, brsh: QtGui.QBrush):
        self._on_color = brsh

    @Property(QtGui.QColor)
    def offColor(self):
        return self._off_color

    @offColor.setter
    def offColor(self, brsh: QtGui.QBrush):
        self._off_color = brsh

    @Property(float)
    def offset(self):
        return self._x

    @offset.setter
    def offset(self, o: float):
        self._x = o
        self.update()

    @Property(QtGui.QColor)
    def handleColor(self):
        return self._handle_color

    @handleColor.setter
    def handleColor(self, color: QtGui.QColor):
        self._handle_color = color

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(
            2 * (self._height + self._margin), self._height + 2 * self._margin
        )

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        _y = self._height / 2
        rrect = QtCore.QRect(
            self._margin,
            self._margin,
            self.width() - 2 * self._margin,
            self.height() - 2 * self._margin,
        )
        if self.isEnabled():
            p.setBrush(self._on_color if self._checked else self._off_color)
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        else:
            p.setBrush(self._off_color)
            p.setOpacity(0.66)
        p.drawRoundedRect(rrect, _y, _y)
        p.setBrush(self._handle_color)
        p.setOpacity(1.0)
        p.drawEllipse(QtCore.QRectF(self.offset - _y, 0, self.height(), self.height()))

    def mouseReleaseEvent(self, e):
        if e.button() & Qt.MouseButton.LeftButton:
            self.setChecked(not self.checked())
        return super().mouseReleaseEvent(e)

    def enterEvent(self, e):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        return super().enterEvent(e)

    def checked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool):
        start = self.positionForValue(self._checked)
        end = self.positionForValue(val)
        self._checked = val
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setDuration(120)
        self._anim.start()
        self.toggled.emit(self._checked)

    def positionForValue(self, val: bool) -> int:
        if val:
            return int(self.width() - self._height)
        else:
            return self._height // 2


class QToggleSwitchBase(QtW.QWidget):
    toggled = Signal(bool)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._switch = QToggleSwitch(self)
        self._text = QtW.QLabel(self)
        layout.addWidget(self._switch)
        layout.addWidget(self._text)
        self.setLayout(layout)
        self._switch.toggled.connect(self.toggled)

    def isChecked(self):
        return self._switch.checked()

    def setChecked(self, val: bool):
        self._switch.setChecked(val)

    def text(self):
        return self._text.text()

    def setText(self, text: str):
        self._text.setText(text)


class ToggleSwitch(ButtonWidget):
    def __init__(self, **kwargs):
        super().__init__(
            widget_type=QBaseButtonWidget,
            backend_kwargs={"qwidg": QToggleSwitchBase},
            **kwargs,
        )
        self.native: QToggleSwitchBase
