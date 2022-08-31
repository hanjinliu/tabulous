from __future__ import annotations
from typing import Any, Callable
import pandas as pd

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
