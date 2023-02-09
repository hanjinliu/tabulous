from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Signal


class QIntOrNoneValidator(QtGui.QIntValidator):
    def validate(self, input: str, pos: int) -> tuple[QtGui.QValidator.State, str, int]:
        if input == "":
            return QtGui.QValidator.State.Acceptable, input, pos
        return super().validate(input, pos)


class QIntOrNoneEdit(QtW.QLineEdit):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setValidator(QIntOrNoneValidator)

    def value(self):
        return int(self.text()) if self.text() else None

    def setValue(self, val: int | None):
        self.setText(str(val) if val is not None else "")


class QSelectionRangeEdit(QtW.QWidget):
    sliceChanged = Signal(object)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        layout = QtW.QHBoxLayout()
        self.setLayout(layout)
        self._r_start = QIntOrNoneEdit()
        self._r_stop = QIntOrNoneEdit()
        self._c_start = QIntOrNoneEdit()
        self._c_stop = QIntOrNoneEdit()
        layout.addWidget(self._r_start)
        layout.addWidget(QtW.QLabel(":"))
        layout.addWidget(self._r_stop)
        layout.addWidget(QtW.QLabel(", "))
        layout.addWidget(self._c_start)
        layout.addWidget(QtW.QLabel(":"))
        layout.addWidget(self._c_stop)

    def slice(self) -> tuple[slice, slice]:
        rsl = slice(self._r_start.value(), self._r_stop.value())
        csl = slice(self._c_start.value(), self._c_stop.value())
        return rsl, csl

    def setSlice(self, sl: tuple[slice, slice]):
        rsl, csl = sl
        self._r_start.setValue(rsl.start)
        self._r_stop.setValue(rsl.stop)
        self._c_start.setValue(csl.start)
        self._c_stop.setValue(csl.stop)
        return None
