from __future__ import annotations
from typing import Callable, Any
from enum import Enum, auto
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
import numpy as np
import pandas as pd
from magicgui.widgets import RadioButtons

from tabulous._dtype import get_dtype, isna
from tabulous.widgets import Table

__all__ = ["exec_formatter_dialog"]


def _format_float(value, ndigits: int = 4) -> str:
    """convert string to int or float if possible"""
    if isna(value):
        text = "nan"
    elif 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = f"{value:.{ndigits}f}"
    else:
        text = f"{value:.{ndigits-1}e}"

    return text


def _format_int(value, ndigits: int = 4) -> str:
    if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = str(value)
    else:
        text = f"{value:.{ndigits-1}e}"

    return text


def _format_complex(value: complex, ndigits: int = 3) -> str:
    if isna(value):
        text = "nan"
    elif 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = f"{value.real:.{ndigits}f}{value.imag:+.{ndigits}f}j"
    else:
        text = f"{value.real:.{ndigits-1}e}{value.imag:+.{ndigits-1}e}j"

    return text


_DEFAULT_FORMATTERS: dict[str, Callable[[Any], str]] = {
    "u": _format_int,
    "i": _format_int,
    "f": _format_float,
    "c": _format_complex,
}


class DefaultFormatter:
    """
    The default formatter function.

    This class is a simple wrapper around a callable. Spreadsheet needs to know if
    a formatter is the default one when dtype is changed.
    """

    def __init__(self, dtype: Any):
        self._dtype = get_dtype(dtype)
        self._formatter = _DEFAULT_FORMATTERS.get(self._dtype.kind, str)

    def __call__(self, value: Any) -> None:
        return self._formatter(value)

    def __repr__(self) -> str:
        return f"DefaultFormatter[{self._dtype.name}]"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, DefaultFormatter):
            return False
        return self._dtype == other._dtype


class NumberFormat(Enum):
    """Formats used for integers."""

    default = auto()
    decimal = auto()
    exponential = auto()


class FloatFormat(Enum):
    """Formats used for floating numbers."""

    default = auto()
    decimal = auto()
    exponential = auto()
    percent = auto()


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
    hour_min_second = auto()
    min_second = auto()
    hour_min = auto()


class QDigitsSpinBox(QtW.QSpinBox):
    def __init__(self, value: int = 4):
        super().__init__()
        self.setMinimum(0)
        self.setMaximum(12)
        self.setValue(value)
        self.setSuffix(" digits")
        self.setToolTip("Number of digits to display.")


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
    _ENUM = NumberFormat

    def _init(self) -> None:
        btns = RadioButtons(choices=self._ENUM, value=self._ENUM.default)
        self._btns = btns
        self.addWidget(btns.native)

        self._ndigits = QDigitsSpinBox()
        self.addWidget(self._ndigits)

        btns.changed.connect(self._on_choice_changed)
        self._ndigits.valueChanged.connect(lambda: self._on_choice_changed())

    def _on_choice_changed(self, val=None):
        raise NotImplementedError()


class QIntFormatterDialog(_QNumberFormatterDialog):
    def _on_choice_changed(self, val=None):
        if val is None:
            val = self._btns.value
        val = self._ENUM(val)
        self._ndigits.setVisible(val == self._ENUM.exponential)
        self._preview_table.text_formatter(self._name, self.toFormatter(val))
        return self._preview_table.refresh()

    def toFormatter(self, val=None) -> str:
        """Convert widget paramters to a formatter text."""
        if val is None:
            val = self._btns.value

        n = self._ndigits.value()
        if val == self._ENUM.default:
            fmt = None
        elif val == self._ENUM.decimal:
            fmt = "{}"
        elif val == self._ENUM.exponential:
            fmt = f"{{:.{n}g}}"
        else:
            raise RuntimeError()
        return fmt


class QFloatFormatterDialog(_QNumberFormatterDialog):
    _ENUM = FloatFormat

    def _on_choice_changed(self, val=None):
        if val is None:
            val = self._btns.value
        val = self._ENUM(val)
        self._ndigits.setVisible(val != self._ENUM.default)
        self._preview_table.text_formatter(self._name, self.toFormatter(val))
        return self._preview_table.refresh()

    def toFormatter(self, val=None) -> str:
        """Convert widget paramters to a formatter text."""
        if val is None:
            val = self._btns.value

        n = self._ndigits.value()
        if val == self._ENUM.default:
            fmt = None
        elif val == self._ENUM.decimal:
            fmt = f"{{:.{n}f}}"
        elif val == self._ENUM.exponential:
            fmt = f"{{:.{n}g}}"
        elif val == self._ENUM.percent:
            fmt = f"{{:.{n}%}}"
        else:
            raise RuntimeError()
        return fmt


class QComplexFormatterDialog(_QNumberFormatterDialog):
    _ENUM = ComplexFormat

    def _init(self) -> None:
        super()._init()
        self._iunit = QtW.QLineEdit("j")
        self._iunit.setToolTip("Imaginary unit.")
        self._iunit.textChanged.connect(lambda: self._on_choice_changed())
        self.addWidget(self._iunit)

    def _on_choice_changed(self, val=None):
        if val is None:
            val = self._btns.value
        val = self._ENUM(val)
        self._ndigits.setVisible(val != self._ENUM.default)
        self._preview_table.text_formatter(self._name, self.toFormatter(val))
        return self._preview_table.refresh()

    def toFormatter(self, val=None) -> None | Callable[[complex], str]:
        """Convert widget paramters to a formatter text."""
        if val is None:
            val = self._btns.value
        iunit = self._iunit.text()
        n = self._ndigits.value()
        if val == self._ENUM.default:
            return None
        elif val == self._ENUM.decimal:
            return lambda x: f"{x.real:.{n}f}{x.imag:+.{n}f}{iunit}"
        elif val == self._ENUM.exponential:
            return lambda x: f"{x.real:.{n}e}{x.imag:+.{n}e}{iunit}"
        elif val == self._ENUM.polar:
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

        self._ndigits = QDigitsSpinBox(0)
        self.addWidget(self._ndigits)

        self._btns.changed.connect(lambda: self._on_choice_changed())
        self._ndigits.valueChanged.connect(lambda: self._on_choice_changed())

    def _on_choice_changed(self, val=None):
        return self._preview_table.text_formatter(self._name, self.toFormatter(val))

    def toFormatter(self, val: str = None) -> Callable[[pd.Timedelta], str]:
        """Convert widget paramters to a formatter text."""
        if val is None:
            val = self._btns.value
        val = TimedeltaFormat(val)
        n = self._ndigits.value()

        if val == TimedeltaFormat.default:
            return lambda td: str(td)
        elif val == TimedeltaFormat.day:
            return lambda td: f"{td.days} days"
        elif val == TimedeltaFormat.hour:
            return lambda td: f"{td.total_seconds() / 3600:.{n}f} h"
        elif val == TimedeltaFormat.minute:
            return lambda td: f"{td.total_seconds() / 60:.{n}f} min"
        elif val == TimedeltaFormat.second:
            return lambda td: f"{td.total_seconds():.{n}f} s"
        elif val == TimedeltaFormat.hour_min_second:
            return lambda td: _to_hms(td, n)
        elif val == TimedeltaFormat.hour_min:
            return lambda td: _to_hm(td, n)
        elif val == TimedeltaFormat.min_second:
            return lambda td: _to_ms(td, n)
        else:
            raise RuntimeError(val)


def _to_hms(td: pd.Timedelta, n: int) -> str:
    """Convert timedelta to hours, minutes, seconds."""
    total_sec = td.total_seconds()
    hours, res_min = divmod(total_sec, 3600)
    minutes, seconds = divmod(res_min, 60)
    if seconds < 10:
        return f"{int(hours):0>2}:{int(minutes):0>2}:0{seconds:.{n}f}"
    return f"{int(hours):0>2}:{int(minutes):0>2}:{seconds:.{n}f}"


def _to_hm(td: pd.Timedelta, n: int) -> str:
    """Convert timedelta to hours, minutes, seconds."""
    total_min = td.total_seconds() / 60
    hours, minutes = divmod(total_min, 60)
    if minutes < 10:
        return f"{int(hours):0>2}:0{minutes:.{n}f}"
    return f"{int(hours):0>2}:{minutes:.{n}f}"


def _to_ms(td: pd.Timedelta, n: int) -> str:
    """Convert timedelta to hours, minutes, seconds."""
    total_sec = td.total_seconds()
    minutes, seconds = divmod(total_sec, 60)
    if seconds < 10:
        return f"{int(minutes):0>2}:0{seconds:.{n}f}"
    return f"{int(minutes):0>2}:{seconds:.{n}f}"


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
