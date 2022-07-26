from __future__ import annotations
from typing import Any
import pandas as pd
from ._base import QMutableSimpleTable, DataFrameModel


class QTableLayer(QMutableSimpleTable):
    def getDataFrame(self) -> pd.DataFrame:
        return self._data_raw

    @QMutableSimpleTable._mgr.interface
    def setDataFrame(self, data: pd.DataFrame) -> None:
        self._data_raw = data
        self.model().df = data
        self.setFilter(None)
        self._qtable_view.viewport().update()
        return

    @setDataFrame.server
    def setDataFrame(self, data):
        try:
            return (self.getDataFrame(),), {}
        except Exception:
            return None

    def createModel(self):
        model = DataFrameModel(self)
        self._qtable_view.setModel(model)
        return None

    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value to the type of the table."""
        kind = self._data_raw.dtypes[c].kind
        return _DTYPE_CONVERTER[kind](value)


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


_NAN_STRINGS = frozenset({"", "nan", "na", "n/a", "<na>", "NaN", "NA", "N/A", "<NA>"})


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
