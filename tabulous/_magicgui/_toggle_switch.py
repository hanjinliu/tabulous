from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal, Property

try:
    from magicgui.widgets.bases import ButtonWidget, CategoricalWidget
except ImportError:
    from magicgui.widgets._bases import ButtonWidget, CategoricalWidget
from magicgui.backends._qtpy.widgets import (
    QBaseButtonWidget,
    RadioButtons as RadioButtonsBase,
    QBaseValueWidget,
)
from magicgui.widgets import RadioButtons, Select


class QToggleSwitch(QtW.QWidget):
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
        self.toggled.connect(self._set_checked)

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

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() & Qt.MouseButton.LeftButton:
            self.toggled.emit(not self.isChecked())
        return super().mouseReleaseEvent(e)

    def enterEvent(self, e):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        return super().enterEvent(e)

    def toggle(self):
        return self.setChecked(not self.isChecked())

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool):
        self._set_checked(val)
        self.toggled.emit(val)

    def _set_checked(self, val: bool):
        start = self.positionForValue(self._checked)
        end = self.positionForValue(val)
        self._checked = val
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setDuration(120)
        self._anim.start()

    def positionForValue(self, val: bool) -> int:
        if val:
            return int(self.width() - self._height)
        else:
            return self._height // 2


class QToggleSwitchBase(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._switch = QToggleSwitch(self)
        self._text = QtW.QLabel(self)
        layout.addWidget(self._switch)
        layout.addWidget(self._text)
        self.setLayout(layout)

    def enterEvent(self, e):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        return super().enterEvent(e)

    def isChecked(self) -> bool:
        return self._switch.isChecked()

    def setChecked(self, val: bool):
        self._switch.setChecked(val)

    def isDown(self) -> bool:
        return self.isChecked()

    def setDown(self, a0: bool) -> None:
        return self.setChecked(a0)

    def text(self) -> str:
        return self._text.text()

    def setText(self, text: str):
        self._text.setText(text)

    def click(self):
        self.toggle()

    def toggle(self):
        self.setChecked(not self.isChecked())

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        return QtW.QWidget.paintEvent(self, e)


class QButtonGroup(QtCore.QObject):
    buttonToggled = Signal(QToggleSwitchBase, bool)

    def __init__(self) -> None:
        super().__init__()
        self._list: list[QToggleSwitchBase] = []
        self._exclusive = True

    def buttons(self) -> list[QToggleSwitchBase]:
        return self._list

    def checkedButton(self) -> QToggleSwitchBase:
        for btn in self._list:
            if btn.isChecked():
                return btn
        return None

    def checkedButtons(self) -> list[QToggleSwitchBase]:
        return [btn for btn in self._list if btn.isChecked()]

    def addButton(self, btn: QToggleSwitchBase):
        self._list.append(btn)
        btn._switch.toggled.connect(
            lambda checked: self._on_button_toggled(btn, checked)
        )

    def removeButton(self, btn: QToggleSwitchBase):
        self._list.remove(btn)
        btn._switch.toggled.disconnect()

    def exclusive(self) -> bool:
        return self._exclusive

    def setExclusive(self, val: bool):
        self._exclusive = val

    def _on_button_toggled(self, btn: QToggleSwitchBase, checked: bool):
        if self.exclusive():
            if checked:
                for b in self._list:
                    if b is not btn:
                        b._switch._set_checked(False)
            else:
                btn._switch._set_checked(True)
        self.buttonToggled.emit(btn, checked)


class QToggleSwitchesBase(RadioButtonsBase):
    _qwidget: QtW.QGroupBox

    def __init__(self, **kwargs):
        QBaseValueWidget.__init__(self, QtW.QGroupBox, "", "", "", **kwargs)
        self._btn_group = QButtonGroup()
        self._qwidget.setLayout(QtW.QVBoxLayout())
        self._btn_group.buttonToggled.connect(self._emit_data)

    def _emit_data(self, btn, checked):
        if checked or not self._btn_group.exclusive():
            self._event_filter.valueChanged.emit(self._mgui_get_value())

    def _add_button(self, label: str, data=None):
        btn = QToggleSwitchBase(self._qwidget)
        btn.setText(label)
        btn._data = data
        self._btn_group.addButton(btn)
        self._qwidget.layout().addWidget(btn)

    def _mgui_get_value(self):
        if self._btn_group.exclusive():
            btn = self._btn_group.checkedButton()
            return btn._data if btn else None
        else:
            return [btn._data for btn in self._btn_group.checkedButtons()]

    def _mgui_set_value(self, value) -> None:
        if self._btn_group.exclusive():
            for btn in self._btn_group.buttons():
                if btn._data == value:
                    btn._switch._set_checked(True)
                    break  # exclusive
        else:
            for btn in self._btn_group.buttons():
                btn._switch._set_checked(btn._data in value)


class ToggleSwitch(ButtonWidget):
    def __init__(self, **kwargs):
        super().__init__(
            widget_type=QBaseButtonWidget,
            backend_kwargs={"qwidg": QToggleSwitchBase},
            **kwargs,
        )
        self.native: QToggleSwitchBase


class ToggleSwitches(RadioButtons):  # type: ignore
    """An radio buttons using toggle switches."""

    def __init__(self, choices=(), orientation="vertical", **kwargs):
        kwargs["widget_type"] = QToggleSwitchesBase
        CategoricalWidget.__init__(self, choices=choices, **kwargs)
        self.orientation = orientation


class ToggleSwitchSelect(Select):
    def __init__(self, choices=(), orientation="vertical", **kwargs):
        kwargs["widget_type"] = QToggleSwitchesBase
        CategoricalWidget.__init__(self, choices=choices, **kwargs)
        self._widget._btn_group.setExclusive(False)
        self.orientation = orientation
