from __future__ import annotations
from typing import Any, Callable
import pandas as pd
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

_NAN_STRINGS = frozenset({"", "nan", "na", "n/a", "<na>", "NaN", "NA", "N/A", "<NA>"})


def _bool_converter(val: Any):
    if isinstance(val, str):
        if val in ("True", "1", "true"):
            return True
        elif val in ("False", "0", "false"):
            return False
        else:
            raise ValueError(f"Cannot convert {val} to bool.")
    else:
        return bool(val)


def _float_or_nan(x: Any):
    if x in _NAN_STRINGS:
        return float("nan")
    return float(x)


def _complex_or_nan(x: Any):
    if x in _NAN_STRINGS:
        return float("nan")
    return complex(x)


_DTYPE_CONVERTER = {
    "i": int,
    "f": _float_or_nan,
    "u": int,
    "b": _bool_converter,
    "U": str,
    "O": lambda e: e,
    "c": _complex_or_nan,
    "M": pd.to_datetime,
    "m": pd.to_timedelta,
}


def convert_value(kind: str, value: Any) -> Any:
    """Convert value according to the dtype kind."""
    return _DTYPE_CONVERTER[kind](value)


def get_converter(kind: str) -> Callable[[Any], Any]:
    return _DTYPE_CONVERTER[kind]


class QDtypeWidget(QtW.QTreeWidget):
    _DTYPES = [
        "unset",
        "int",
        "uint",
        "float",
        "complex",
        "bool",
        "time",
        "others",
    ]

    _SUB_DTYPES = {
        "int": ["int8", "int16", "int32", "int64"],
        "uint": ["uint8", "uint16", "uint32", "uint64"],
        "float": ["float16", "float32", "float64"],
        "complex": ["complex64", "complex128"],
        "time": ["datetime64", "timedelta64"],
        "others": [
            "category",
            "string",
            "object",
        ],
    }

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setHeaderHidden(True)

        for dtype in self._DTYPES:
            item = QtW.QTreeWidgetItem([dtype])
            self.addTopLevelItem(item)
            if sub := self._SUB_DTYPES.get(dtype, None):
                item.addChildren(QtW.QTreeWidgetItem([s]) for s in sub)

        self.setSelectionMode(QtW.QTreeWidget.SelectionMode.SingleSelection)

    def dtypeText(self) -> str:
        """Get the selected dtype as a text."""
        return self.currentItem().text(0)

    @classmethod
    def requestValue(cls, parent=None) -> str | None:
        self = cls()
        dlg = QtW.QDialog(parent)
        dlg.setLayout(QtW.QVBoxLayout())
        dlg.layout().addWidget(QtW.QLabel("dtype"))
        dlg.layout().addWidget(self)

        _Btn = QtW.QDialogButtonBox.StandardButton
        _btn_box = QtW.QDialogButtonBox(
            _Btn.Ok | _Btn.Cancel,
            Qt.Orientation.Horizontal,
        )
        _btn_box.accepted.connect(dlg.accept)
        _btn_box.rejected.connect(dlg.reject)
        dlg.layout().addWidget(_btn_box)
        dlg.setWindowTitle("Select a dtype")
        if dlg.exec():
            out = self.dtypeText()
        else:
            out = None
        return out
