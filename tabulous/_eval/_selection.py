from __future__ import annotations

from typing import Hashable, Iterator, TYPE_CHECKING
from functools import singledispatch
import re

if TYPE_CHECKING:
    import pandas as pd


class SelectionOperator:
    """An object that defines a selection on a dataframe."""

    def fmt(self) -> str:
        """Format selection literal for display."""
        raise NotImplementedError()

    def __repr__(self) -> str:
        cname = type(self).__name__
        return f"{cname}({self.fmt()})"

    def operate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Slice dataframe according to selection literal."""
        raise NotImplementedError()

    def as_iloc(self, df: pd.DataFrame) -> tuple[int | slice, int | slice]:
        """Return selection literal as iloc indices."""
        raise NotImplementedError()


class ColumnSelOp(SelectionOperator):
    """An object that represents selection such as ``df["foo"][2:5]``."""

    def __init__(self, col: Hashable, rows: slice):
        self.args = (col, rows)

    def fmt(self) -> str:
        col, rows = self.args
        return f"df[{_fmt_slice(col)!r}][{_fmt_slice(rows)!r}]"

    def operate(self, df: pd.DataFrame) -> pd.DataFrame:
        col, rows = self.args
        return df[col][rows]

    def as_iloc(self, df: pd.DataFrame) -> tuple[int | slice, int | slice]:
        colname, rsel = self.args
        col = df.columns.get_loc(colname)
        return rsel, col


class LocSelOp(SelectionOperator):
    """An object that represents selection such as ``df.loc["foo":"bar", 2:5]``."""

    def __init__(self, rsel: Hashable | slice, csel: Hashable | slice):
        self.args = (rsel, csel)

    def fmt(self) -> str:
        rsel, csel = self.args
        return f"df.loc[{_fmt_slice(rsel)!r}, {_fmt_slice(csel)!r}]"

    def operate(self, df: pd.DataFrame) -> pd.DataFrame:
        rsel, csel = self.args
        return df.loc[rsel, csel]

    def as_iloc(self, df: pd.DataFrame) -> tuple[int | slice, int | slice]:
        rsel, csel = self.args
        irsel = df.index.get_loc(rsel)
        icsel = df.index.get_loc(csel)
        return irsel, icsel


class ILocSelOp(SelectionOperator):
    """An object that represents selection such as ``df.iloc[4:7, 2:5]``."""

    def __init__(self, rsel: int | slice, csel: int | slice):
        self.args = (rsel, csel)

    def fmt(self) -> str:
        rsel, csel = self.args
        return f"df.iloc[{_fmt_slice(rsel)!r}, {_fmt_slice(csel)!r}]"

    def operate(self, df: pd.DataFrame) -> pd.DataFrame:
        rsel, csel = self.args
        return df.iloc[rsel, csel]

    def as_iloc(self, df: pd.DataFrame) -> tuple[int | slice, int | slice]:
        return self.args


def iter_extract(text: str, *, df_expr: str = "df") -> Iterator[SelectionOperator]:
    """Iteratively extract selection literal from text."""
    ndf = len(df_expr)
    for expr in _find_all_dataframe_expr(text):
        if expr.startswith(f"{df_expr}["):
            # df['val'][...]
            colname, rsl_str = expr[ndf + 1 : -1].split("][")
            rsl = _parse_slice(rsl_str)
            sel = ColumnSelOp(colname, rsl)

        elif expr.startswith(f"{df_expr}.loc["):
            # df.loc[..., ...]
            rsl_str, csl_str = expr[ndf + 5 : -1].split(",")
            rsl = _parse_slice(rsl_str)
            csl = _parse_slice(csl_str)
            sel = LocSelOp(rsl, csl)

        elif expr.startswith(f"{df_expr}.iloc["):
            # df.iloc[..., ...]
            rsl_str, csl_str = expr[ndf + 6 : -1].split(",")
            rsl = _parse_slice(rsl_str)
            csl = _parse_slice(csl_str)
            sel = ILocSelOp(rsl, csl)

        else:
            raise ValueError(f"Unreachable expression: {expr!r}")

        yield sel


_PATTERN = re.compile(r"df\[.+?\]\[.+?\]|df\.loc\[.+?\]|df\.iloc\[.+?\]")


def _find_all_dataframe_expr(s: str) -> list[str]:
    return _PATTERN.findall(s)


def _eval(expr: str, default=None):
    """evaluate expression."""
    return eval(expr, {}, {}) if expr else default


def _parse_slice(s: str) -> slice:
    s = s.strip()
    if ":" in s:
        start_str, stop_str = s.split(":")
        start = _eval(start_str)
        stop = _eval(stop_str)
    else:
        start = _eval(s)
        stop = start + 1
    return slice(start, stop)


@singledispatch
def _fmt_slice(s) -> str:
    return str(s)


@_fmt_slice.register
def _(s: slice) -> str:
    if s == slice(None):
        return ":"
    start = "" if s.start is None else s.start
    stop = "" if s.stop is None else s.stop
    return f"{start}:{stop}"
