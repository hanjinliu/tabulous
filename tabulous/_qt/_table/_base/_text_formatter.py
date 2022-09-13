from __future__ import annotations
from typing import Callable
from enum import Enum, auto
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
import numpy as np
import pandas as pd
from magicgui.widgets import RadioButtons

from ....widgets import Table

__all__ = ["exec_formatter_dialog"]


class NumberFormat(Enum):
    """Formats used for real numbers."""

    default = auto()
    decimal = auto()
    exponential = auto()


class ComplexFormat(Enum):
    """Formats used for complex numbers."""

    default = auto()
    decimal = auto()
    exponential = auto()
    polar = auto()


class TimedeltaFormat(Enum):
    """Formats used for timedelta."""

    default = auto()
    day = auto()
    hour = auto()
    minute = auto()
    second = auto()


class _QFormatterDialog(QtW.QDialog):
    def __init__(self, ds: pd.Series, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        _layout = QtW.QHBoxLayout()
        self._name = ds.name
        self._preview_table = Table(ds, editable=False)
        self._preview_table.native.setMaximumWidth(120)
        self._left_panel = QtW.QWidget()
        self._left_panel.setLayout(QtW.QVBoxLayout())
        self._left_panel.layout().setContentsMargins(0, 0, 0, 0)

        _layout.addWidget(self._left_panel)
        _layout.addWidget(titled("Preview", self._preview_table.native))
        self._init()
        self.setLayout(_layout)
        btnbox = QtW.QDialogButtonBox(
            QtW.QDialogButtonBox.StandardButton.Ok
            | QtW.QDialogButtonBox.StandardButton.Cancel,
        )
        btnbox.accepted.connect(self.accept)
        btnbox.rejected.connect(self.reject)
        self.addWidget(btnbox)
        self.resize(450, 320)

    def _init(self):
        """Initialize UI."""

    def addWidget(self, widget: QtW.QWidget):
        self._left_panel.layout().addWidget(widget)
        return None

    def toFormatter(self, val=None) -> str:
        """Convert widget paramters to a formatter text."""
        raise NotImplementedError()


class _QNumberFormatterDialog(_QFormatterDialog):
    def _init(self) -> None:
        btns = RadioButtons(choices=NumberFormat, value=NumberFormat.default)
        self._btns = btns
        self.addWidget(btns.native)

        self._ndigits = QtW.QSpinBox()
        self._ndigits.setMinimum(1)
        self._ndigits.setMaximum(12)
        self._ndigits.setValue(4)
        self._ndigits.setSuffix(" digits")
        self.addWidget(self._ndigits)

        btns.changed.connect(self._on_choice_changed)
        self._ndigits.valueChanged.connect(lambda: self._on_choice_changed())

    def _on_choice_changed(self, val=None):
        raise NotImplementedError()


class QIntFormatterDialog(_QNumberFormatterDialog):
    def _on_choice_changed(self, val=None):
        if val is None:
            val = self._btns.value
        val = NumberFormat(val)
        self._ndigits.setVisible(val == NumberFormat.exponential)
        self._preview_table.text_formatter(self._name, self.toFormatter(val))
        return self._preview_table.refresh()

    def toFormatter(self, val=None) -> str:
        """Convert widget paramters to a formatter text."""
        if val is None:
            val = self._btns.value

        n = self._ndigits.value()
        if val == NumberFormat.default:
            fmt = "default"
        elif val == NumberFormat.decimal:
            fmt = "{}"
        elif val == NumberFormat.exponential:
            fmt = f"{{:.{n}g}}"
        else:
            raise RuntimeError()
        return fmt


class QFloatFormatterDialog(_QNumberFormatterDialog):
    def _on_choice_changed(self, val=None):
        if val is None:
            val = self._btns.value
        val = NumberFormat(val)
        self._ndigits.setVisible(val != NumberFormat.default)
        self._preview_table.text_formatter(self._name, self.toFormatter(val))
        return self._preview_table.refresh()

    def toFormatter(self, val=None) -> str:
        """Convert widget paramters to a formatter text."""
        if val is None:
            val = self._btns.value

        n = self._ndigits.value()
        if val == NumberFormat.default:
            fmt = "default"
        elif val == NumberFormat.decimal:
            fmt = f"{{:.{n}f}}"
        elif val == NumberFormat.exponential:
            fmt = f"{{:.{n}g}}"
        else:
            raise RuntimeError()
        return fmt


class QComplexFormatterDialog(_QFormatterDialog):
    def _init(self) -> None:
        btns = RadioButtons(choices=ComplexFormat, value=ComplexFormat.default)
        self._btns = btns
        self.addWidget(btns.native)

        self._ndigits = QtW.QSpinBox()
        self._ndigits.setMinimum(1)
        self._ndigits.setMaximum(12)
        self._ndigits.setValue(4)
        self._ndigits.setSuffix(" digits")
        self.addWidget(self._ndigits)

        self._iunit = QtW.QLineEdit("j")
        self.addWidget(self._iunit)

        btns.changed.connect(self._on_choice_changed)
        self._ndigits.valueChanged.connect(lambda: self._on_choice_changed())
        self._iunit.textChanged.connect(lambda: self._on_choice_changed())

    def _on_choice_changed(self, val=None):
        if val is None:
            val = self._btns.value
        val = ComplexFormat(val)
        self._ndigits.setVisible(val != ComplexFormat.default)
        self._preview_table.text_formatter(self._name, self.toFormatter(val))
        return self._preview_table.refresh()

    def toFormatter(self, val=None) -> str | Callable[[complex], str]:
        """Convert widget paramters to a formatter text."""
        if val is None:
            val = self._btns.value
        iunit = self._iunit.text()
        n = self._ndigits.value()
        if val == ComplexFormat.default:
            return "default"
        elif val == ComplexFormat.decimal:
            return lambda x: f"{x.real:.{n}f}{x.imag:+.{n}f}{iunit}"
        elif val == ComplexFormat.exponential:
            return lambda x: f"{x.real:.{n}e}{x.imag:+.{n}e}{iunit}"
        elif val == ComplexFormat.polar:
            return lambda x: f"{abs(x):.{n}f}e^({np.angle(x):+.{n}f}{iunit})"
        else:
            raise RuntimeError(val)


class QBoolFormatterDialog(_QFormatterDialog):
    def _init(self) -> None:
        self._true = QtW.QLineEdit("True")
        self._false = QtW.QLineEdit("False")
        self._true.textChanged.connect(self._on_text_changed)
        self._false.textChanged.connect(self._on_text_changed)
        self.addWidget(labeled("True:", self._true, 50))
        self.addWidget(labeled("False:", self._false, 50))

    def _on_text_changed(self, val=None):
        return self._preview_table.text_formatter(self._name, self.toFormatter(val))

    def toFormatter(self, val=None) -> Callable[[bool], str]:
        """Convert widget paramters to a formatter text."""
        return lambda x: self._true.text() if x else self._false.text()


class QDateTimeFormatterDialog(_QFormatterDialog):
    def _init(self) -> None:
        label = QtW.QLabel(
            "%Y: year\n"
            "%m: month\n"
            "%d: day\n"
            "%H: hour\n"
            "%M: minute\n"
            "%S: second\n"
        )
        self._fmt = QtW.QLineEdit("%Y-%m-%d")
        self.addWidget(label)
        self.addWidget(labeled("Format:", self._fmt))
        self._fmt.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, val=None):
        return self._preview_table.text_formatter(self._name, self.toFormatter(val))

    def toFormatter(self, val: str = None) -> Callable[[pd.Timestamp], str]:
        """Convert widget paramters to a formatter text."""
        if val is None:
            val = self._fmt.text()

        return lambda ts: ts.strftime(val)


class QTimeDeltaFormatterDialog(_QFormatterDialog):
    def _init(self) -> None:
        self._btns = RadioButtons(
            choices=TimedeltaFormat, value=TimedeltaFormat.default
        )
        self.addWidget(self._btns.native)
        self._btns.changed.connect(lambda: self._on_choice_changed())

    def _on_choice_changed(self, val=None):
        return self._preview_table.text_formatter(self._name, self.toFormatter(val))

    def toFormatter(self, val: str = None) -> Callable[[pd.Timedelta], str]:
        """Convert widget paramters to a formatter text."""
        if val is None:
            val = self._btns.value
        val = TimedeltaFormat(val)

        if val == TimedeltaFormat.default:
            return lambda td: str(td)
        elif val == TimedeltaFormat.day:
            return lambda td: f"{td.days} days"
        elif val == TimedeltaFormat.hour:
            return lambda td: f"{td.total_seconds() // 3600} h"
        elif val == TimedeltaFormat.minute:
            return lambda td: f"{td.total_seconds() // 60} min"
        elif val == TimedeltaFormat.second:
            return lambda td: f"{td.total_seconds()} s"
        else:
            raise RuntimeError(val)


class _LabeledWidget(QtW.QWidget):
    def __init__(
        self,
        label: str,
        widget: QtW.QWidget,
        width: int | None = None,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
    ):
        super().__init__()
        self._label = QtW.QLabel(label)
        self._widget = widget
        if orientation == Qt.Orientation.Horizontal:
            layout = QtW.QHBoxLayout()
            layout.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        elif orientation == Qt.Orientation.Vertical:
            layout = QtW.QVBoxLayout()
            layout.setAlignment(
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter
            )
            self._label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._label)
        layout.addWidget(self._widget)
        self.setLayout(layout)

        if width is not None and orientation == Qt.Orientation.Horizontal:
            self._label.setFixedWidth(width)


def labeled(label: str, widget: QtW.QWidget, width: int | None = None) -> QtW.QWidget:
    """Create a widget with a label."""
    return _LabeledWidget(label, widget, width)


def titled(title: str, widget: QtW.QWidget) -> QtW.QWidget:
    """Create a widget with a title."""
    return _LabeledWidget(title, widget, orientation=Qt.Orientation.Vertical)


def exec_formatter_dialog(ds: pd.Series, parent=None):
    dtype = ds.dtype
    if dtype.kind in "ui":
        dlg = QIntFormatterDialog(ds, parent=parent)
    elif dtype.kind == "f":
        dlg = QFloatFormatterDialog(ds, parent=parent)
    elif dtype.kind == "b":
        dlg = QBoolFormatterDialog(ds, parent=parent)
    elif dtype.kind == "c":
        dlg = QComplexFormatterDialog(ds, parent=parent)
    elif dtype.kind == "M":
        dlg = QDateTimeFormatterDialog(ds, parent=parent)
    elif dtype.kind == "m":
        dlg = QTimeDeltaFormatterDialog(ds, parent=parent)
    else:
        raise ValueError(f"Dtype {dtype.name} is not supported.")

    if dlg.exec():
        return dlg.toFormatter()
    return None
