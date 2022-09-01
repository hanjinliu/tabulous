from __future__ import annotations
from typing import (
    Any,
    Callable,
    Hashable,
    Iterator,
    MutableMapping,
    TYPE_CHECKING,
    TypeVar,
    Union,
)
import numpy as np
import pandas as pd
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt

if TYPE_CHECKING:
    from pandas.core.dtypes.dtypes import ExtensionDtype

    _DTypeLike = Union[np.dtype, ExtensionDtype]

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

        @self.doubleClicked.connect
        def _on_double_click(index: QtCore.QModelIndex):
            item = self.itemFromIndex(index)
            if item.childCount() == 0:
                dlg.accept()
            return

        dlg.setWindowTitle("Select a dtype")
        if dlg.exec():
            out = self.dtypeText()
        else:
            out = None
        return out


_K = TypeVar("_K", bound=Hashable)
_V = TypeVar("_V", bound="_DTypeLike")


class DTypeMap(MutableMapping[_K, _V]):
    """
    Mapping storage of dtypes.

    The dtype map cannot be simply represented as a dict because datetime, timedelta
    and complex must be passed differently in pd.read_csv.
    """

    def __init__(self) -> None:
        self._dict: dict[Hashable, _DTypeLike] = {}
        self._datetime_dict: dict[Hashable, _DTypeLike] = {}
        self._need_parsing_dict: dict[Hashable, _DTypeLike] = {}

    def __repr__(self) -> str:
        clsname = type(self).__name__
        return f"{clsname}{dict(**self)!r}"

    def __getitem__(self, key: _K) -> _V:
        out = self._dict.get(key, None)
        if out is None:
            out = self._datetime_dict.get(key, None)
            if out is None:
                out = self._need_parsing_dict[key]
        return out

    def __setitem__(self, key: _K, value: _V) -> None:
        if value.kind not in ("M", "m", "c"):
            self._dict[key] = value
        elif value.kind == "M":
            self._datetime_dict[key] = value
        else:
            self._need_parsing_dict[key] = value

    def __delitem__(self, key: _K) -> None:
        self._dict.pop(key, None) or self._datetime_dict.pop(
            key, None
        ) or self._need_parsing_dict.pop(key, None)
        return None

    def __iter__(self) -> Iterator[_K]:
        yield from iter(self._dict)
        yield from iter(self._datetime_dict)
        yield from iter(self._need_parsing_dict)

    def __len__(self) -> int:
        return len(self._dict) + len(self._datetime_dict) + len(self._need_parsing_dict)

    def as_pandas_kwargs(self) -> dict[str, Any]:
        """Create a dict ready for being passed to ``pd.read_csv``."""
        kwargs = {"dtype": self._dict}
        if self._datetime_dict:
            kwargs.update(
                parse_dates=list(self._datetime_dict.keys()),
                infer_datetime_format=True,
            )
        if self._need_parsing_dict:
            kwargs.update(
                converters={
                    k: get_converter(v.kind) for k, v in self._need_parsing_dict.items()
                },
            )
        return kwargs
