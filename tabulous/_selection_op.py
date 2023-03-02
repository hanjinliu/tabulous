from __future__ import annotations

from typing import Hashable, Iterator, TYPE_CHECKING, Literal, Union, SupportsIndex
from functools import singledispatch
import re

from tabulous.exceptions import UnreachableError

if TYPE_CHECKING:
    import pandas as pd
    from typing_extensions import Self

_Slice = Union[int, slice]
_SlicePattern = r"(\w|:|-|\s)"


class SelectionOperator:
    """An object that defines a selection on a dataframe."""

    args: tuple
    PATTERN: str

    def fmt(self, df_expr: str = "df") -> str:
        """Format selection literal for display."""
        raise NotImplementedError()

    def fmt_iloc(self, df: pd.DataFrame, df_expr: str = "df") -> str:
        """Format selection literal as iloc indices."""
        rsel, csel = self.as_iloc(df)
        return f"{df_expr}.iloc[{_fmt_slice(rsel)}, {_fmt_slice(csel)}]"

    def fmt_scalar(self, df_expr: str = "df") -> str:
        """Format 1x1 selection literal as a scalar reference."""
        raise NotImplementedError()

    def resolve_indices(self, df: pd.DataFrame, shape: tuple[int, int]):
        rsel, csel = self.as_iloc(df)
        nr, nc = shape
        if rsel == slice(None):
            rsel = slice(nr)
        if csel == slice(None):
            csel = slice(nc)
        return self.from_iloc(rsel, csel, df)

    def __format__(self, spec: str) -> str:
        return self.fmt(df_expr=spec)

    def __repr__(self) -> str:
        cname = type(self).__name__
        return f"{cname}({self.fmt()})"

    def operate(self, df: pd.DataFrame) -> pd.DataFrame | pd.Series:
        """Slice dataframe according to selection literal."""
        raise NotImplementedError()

    def as_iloc(self, df: pd.DataFrame) -> tuple[_Slice, _Slice]:
        """Return selection literal as iloc indices."""
        raise NotImplementedError()

    def as_iloc_slices(self, df: pd.DataFrame) -> tuple[slice, slice]:
        """Return selection literal as iloc indices, forcing slices."""
        rsl, csl = self.as_iloc(df)
        if isinstance(rsl, SupportsIndex):
            r = rsl.__index__()
            rsl = slice(r, r + 1)
        elif rsl == slice(None):
            rsl = slice(0, df.index.size)
        if isinstance(csl, SupportsIndex):
            c = csl.__index__()
            csl = slice(c, c + 1)
        elif csl == slice(None):
            csl = slice(0, df.columns.size)
        return rsl, csl

    def as_iat(self, df: pd.DataFrame) -> tuple[int, int]:
        rsl, csl = self.as_iloc(df)
        if isinstance(rsl, SupportsIndex):
            r = rsl.__index__()
        elif isinstance(rsl, slice):
            if rsl.stop - rsl.start != 1:
                raise ValueError(f"{self} is not a scalar reference.")
            r = rsl.start
        if isinstance(csl, SupportsIndex):
            c = csl.__index__()
        elif isinstance(csl, slice):
            if csl.stop - csl.start != 1:
                raise ValueError(f"{self} is not a scalar reference.")
            c = csl.start
        return r, c

    def shape(self, df: pd.DataFrame) -> tuple[int, int]:
        """Return the shape of the selection."""
        rsl, csl = self.as_iloc_slices(df)
        return (rsl.stop - rsl.start, csl.stop - csl.start)

    def area(self, df: pd.DataFrame) -> int:
        """Return the number of cells selected."""
        rsl, csl = self.as_iloc_slices(df)
        return (rsl.stop - rsl.start) * (csl.stop - csl.start)

    @classmethod
    def from_iloc(cls, r: _Slice, c: _Slice, df: pd.DataFrame) -> Self:
        """Construct selection literal from iloc indices."""
        raise NotImplementedError()

    def __eq__(self, other: Self) -> bool:
        if isinstance(other, type(self)):
            return self.args == other.args
        return False


class ColumnSelOp(SelectionOperator):
    """An object that represents selection such as ``df["foo"][2:5]``."""

    args: tuple[Hashable, slice]
    PATTERN = r"df\[.+?\]\[.+?\]"

    def __init__(self, col: Hashable, rows: slice):
        self.args = (col, rows)

    def fmt(self, df_expr: str = "df") -> str:
        col, rows = self.args
        return f"{df_expr}[{_fmt_slice(col)}][{_fmt_slice(rows)}]"

    def fmt_scalar(self, df_expr: str = "df") -> str:
        col, rows = self.args
        start, stop = rows.start, rows.stop
        if stop - start != 1:
            raise ValueError("Cannot format as a scalar value.")
        return f"{df_expr}[{_fmt_slice(col)}][{_fmt_slice(start)}]"

    def operate(self, df: pd.DataFrame) -> pd.DataFrame:
        col, rows = self.args
        return df[col][rows]

    def as_iloc(self, df: pd.DataFrame) -> tuple[_Slice, _Slice]:
        colname, rsel = self.args
        col = df.columns.get_loc(colname)
        return rsel, col

    @classmethod
    def from_iloc(cls, r: _Slice, c: _Slice, df: pd.DataFrame) -> Self:
        if isinstance(c, slice):
            if c.start == c.stop - 1:
                c = c.start
            else:
                raise ValueError("Cannot convert slice to row selection.")
        colname = df.columns[c]
        return cls(colname, r)


class LocSelOp(SelectionOperator):
    """An object that represents selection such as ``df.loc["foo":"bar", 2:5]``."""

    PATTERN = r"df\.loc\[.+?\]"

    def __init__(self, rsel: Hashable | slice, csel: Hashable | slice):
        self.args = (rsel, csel)

    def fmt(self, df_expr: str = "df") -> str:
        rsel, csel = self.args
        return f"{df_expr}.loc[{_fmt_slice(rsel)}, {_fmt_slice(csel)}]"

    def fmt_scalar(self, df_expr: str = "df") -> str:
        rsel, csel = self.args
        if isinstance(rsel, slice):
            if _has_none(rsel) or rsel.start != rsel.stop:
                raise ValueError("Cannot format as a scalar value.")
            rsel = rsel.start
        if isinstance(csel, slice):
            if _has_none(csel) or csel.start != csel.stop:
                raise ValueError("Cannot format as a scalar value.")
            csel = csel.start
        return f"{df_expr}.loc[{_fmt_slice(rsel)}, {_fmt_slice(csel)}]"

    def operate(self, df: pd.DataFrame) -> pd.DataFrame:
        rsel, csel = self.args
        return df.loc[rsel, csel]

    def as_iloc(self, df: pd.DataFrame) -> tuple[_Slice, _Slice]:
        rsel, csel = self.args
        index, columns = df.axes
        if isinstance(rsel, slice):
            if rsel.start is None:
                rstart = None
            else:
                rstart = index.get_loc(rsel.start)
            if rsel.stop is None:
                rstop = None
            else:
                rstop = index.get_loc(rsel.stop) + 1
            irsel = slice(rstart, rstop)
        else:
            irsel = index.get_loc(rsel)
        if isinstance(csel, slice):
            if csel.start is None:
                cstart = None
            else:
                cstart = columns.get_loc(csel.start)
            if csel.stop is None:
                cstop = None
            else:
                cstop = columns.get_loc(csel.stop) + 1
            icsel = slice(cstart, cstop)
        else:
            icsel = columns.get_loc(csel)
        return irsel, icsel

    @classmethod
    def from_iloc(cls, r: _Slice, c: _Slice, df: pd.DataFrame) -> Self:
        """Construct operator from an iloc-style slices."""
        index, columns = df.axes
        if isinstance(r, slice):
            rsel = _normalize_loc_slice(r, index)
        else:
            rsel = index[r]
        if isinstance(c, slice):
            csel = _normalize_loc_slice(c, columns)
        else:
            csel = columns[c]
        return cls(rsel, csel)


def _normalize_loc_slice(sl: slice, index: pd.Index) -> slice:
    if sl.start is None:
        start = 0
    else:
        start = sl.start
    if sl.stop is None:
        stop = -1
    else:
        stop = sl.stop
    return slice(index[start], index[stop - 1])


class ILocSelOp(SelectionOperator):
    """An object that represents selection such as ``df.iloc[4:7, 2:5]``."""

    args: tuple[_Slice, _Slice]
    PATTERN = rf"df\.iloc\[{_SlicePattern}+(,{_SlicePattern}*)?\]"

    def __init__(self, rsel: _Slice, csel: _Slice):
        self.args = (rsel, csel)

    def fmt(self, df_expr: str = "df") -> str:
        rsel, csel = self.args
        return f"{df_expr}.iloc[{_fmt_slice(rsel)}, {_fmt_slice(csel)}]"

    def fmt_scalar(self, df_expr: str = "df") -> str:
        rsel, csel = self.args
        if isinstance(rsel, slice):
            if _has_none(rsel) or rsel.start != rsel.stop - 1:
                raise ValueError("Cannot format as a scalar value.")
            rsel = rsel.start
        if isinstance(csel, slice):
            if _has_none(csel) or csel.start != csel.stop - 1:
                raise ValueError("Cannot format as a scalar value.")
            csel = csel.start
        return f"{df_expr}.iloc[{_fmt_slice(rsel)}, {_fmt_slice(csel)}]"

    def operate(self, df: pd.DataFrame) -> pd.DataFrame | pd.Series:
        rsel, csel = self.args
        return df.iloc[rsel, csel]

    def as_iloc(self, df: pd.DataFrame = None) -> tuple[_Slice, _Slice]:
        return self.args

    def as_iloc_slices(self, df: pd.DataFrame | None = None) -> tuple[slice, slice]:
        return super().as_iloc_slices(df)

    @classmethod
    def from_iloc(cls, r: _Slice, c: _Slice, df: pd.DataFrame = None) -> Self:
        """Construct operator from an iloc-style slices."""
        return cls(r, c)


class ValueSelOp(SelectionOperator):
    """An object that represents selection such as ``df.iloc[4:7, 2:5]``."""

    PATTERN = rf"df\.values\[{_SlicePattern}+(,{_SlicePattern}*)?\]"

    def __init__(self, rsel: _Slice, csel: _Slice):
        self.args = (rsel, csel)

    def fmt(self, df_expr: str = "df") -> str:
        rsel, csel = self.args
        return f"{df_expr}.values[{_fmt_slice(rsel)}, {_fmt_slice(csel)}]"

    def fmt_scalar(self, df_expr: str = "df") -> str:
        rsel, csel = self.args
        if isinstance(rsel, slice):
            if _has_none(rsel) or rsel.start != rsel.stop - 1:
                raise ValueError("Cannot format as a scalar value.")
            rsel = rsel.start
        if isinstance(csel, slice):
            if _has_none(csel) or csel.start != csel.stop - 1:
                raise ValueError("Cannot format as a scalar value.")
            csel = csel.start
        return f"{df_expr}.values[{_fmt_slice(rsel)}, {_fmt_slice(csel)}]"

    def operate(self, df: pd.DataFrame) -> pd.DataFrame:
        rsel, csel = self.args
        return df.values[rsel, csel]

    def as_iloc(self, df: pd.DataFrame) -> tuple[_Slice, _Slice]:
        return self.args

    @classmethod
    def from_iloc(cls, r: _Slice, c: _Slice, df: pd.DataFrame) -> Self:
        """Construct operator from an iloc-style slices."""
        return cls(r, c)


def iter_extract(text: str, *, df_expr: str = "df") -> Iterator[SelectionOperator]:
    """Iteratively extract selection literal from text."""
    for match_obj in _PATTERN.finditer(text):
        try:
            op = parse(match_obj.group(), df_expr=df_expr)
        except (ValueError, SyntaxError):
            pass
        else:
            yield op


def iter_extract_with_range(
    text: str,
    *,
    df_expr: str = "df",
) -> Iterator[tuple[tuple[int, int], SelectionOperator]]:
    for match_obj in _PATTERN.finditer(text):
        range = (match_obj.start(), match_obj.end())
        yield range, parse(match_obj.group(), df_expr=df_expr)


def parse(expr: str, *, df_expr: str = "df") -> SelectionOperator:
    """Parse dataframe-slicing expression."""
    ndf = len(df_expr)
    if expr.startswith(f"{df_expr}["):
        # df['val'][...]
        colname, rsl_str = _split_or(expr[ndf + 1 : -1], "][")
        rsl = _parse_slice(rsl_str)
        sel = ColumnSelOp(_eval(colname), rsl)

    elif expr.startswith(f"{df_expr}.loc["):
        # df.loc[..., ...]
        rsl_str, csl_str = _split_or(expr[ndf + 5 : -1], ",")
        rsl = _parse_slice(rsl_str)
        csl = _parse_slice(csl_str)
        sel = LocSelOp(rsl, csl)

    elif expr.startswith(f"{df_expr}.iloc["):
        # df.iloc[..., ...]
        rsl_str, csl_str = _split_or(expr[ndf + 6 : -1], ",")
        rsl = _parse_slice(rsl_str)
        csl = _parse_slice(csl_str)
        sel = ILocSelOp(rsl, csl)

    elif expr.startswith(f"{df_expr}.values["):
        # df.values[..., ...]
        rsl_str, csl_str = _split_or(expr[ndf + 8 : -1], ",")
        rsl = _parse_slice(rsl_str)
        csl = _parse_slice(csl_str)
        sel = ValueSelOp(rsl, csl)

    else:
        raise UnreachableError(f"{expr!r}")

    return sel


def construct(
    rsl: slice,
    csl: slice,
    df: pd.DataFrame,
    method: Literal["loc", "iloc", "values"] = "loc",
    column_selected: bool = False,
    allow_out_of_bounds: bool = False,
) -> SelectionOperator | None:
    """Construct a selection operator from given slices and data frame."""

    nr, nc = df.shape

    # normalize out-of-bound
    if not allow_out_of_bounds:
        rsl = slice(*rsl.indices(nr))
        if rsl.stop > nr:
            if rsl.start >= nr:
                return None
            rsl = slice(rsl.start, nr)
        csl = slice(*csl.indices(nc))
        if csl.stop > nc:
            if csl.start >= nc:
                return None
            csl = slice(csl.start, nc)

    if column_selected:
        rsl = slice(None)

    try:
        if method == "loc":
            if csl.start == csl.stop - 1:
                selop = ColumnSelOp.from_iloc(rsl, csl, df)
            else:
                selop = LocSelOp.from_iloc(rsl, csl, df)
        elif method == "iloc":
            selop = ILocSelOp.from_iloc(rsl, csl, df)
        elif method == "values":
            selop = ValueSelOp.from_iloc(rsl, csl, df)
        else:
            raise RuntimeError(f"Unknwon slicing mode {method!r}")
    except IndexError:
        # out-of-bound in spreadsheet
        return None
    return selop


_PATTERN = re.compile(
    "|".join(s.PATTERN for s in (ColumnSelOp, LocSelOp, ILocSelOp, ValueSelOp))
)


def find_all_dataframe_expr(s: str) -> list[str]:
    return _PATTERN.findall(s)


def find_last_dataframe_expr(s: str) -> int:
    """
    Detect last `df[...][...]` expression from given string.

    Returns start index if matched, otherwise -1.
    """
    _match = None
    for _match in _PATTERN.finditer(s):
        pass
    return _match.start() if _match else -1


def _eval(expr: str, default=None):
    """evaluate expression."""
    return eval(expr, {}, {}) if expr else default


def _parse_slice(s: str) -> Hashable | slice:
    s = s.strip()
    if ":" in s:
        start_str, stop_str = s.split(":")
        start = _eval(start_str)
        stop = _eval(stop_str)
        return slice(start, stop)
    else:
        if s == "":
            return slice(None)
        return _eval(s)


def _has_none(sl: slice):
    return sl.start is None or sl.stop is None


@singledispatch
def _fmt_slice(s) -> str:
    return str(s)


@_fmt_slice.register
def _(s: int) -> str:
    return str(s)


@_fmt_slice.register
def _(s: str) -> str:
    return repr(s)


@_fmt_slice.register
def _(s: slice) -> str:
    if s == slice(None):
        return ":"
    start = "" if s.start is None else s.start
    stop = "" if s.stop is None else s.stop
    return f"{start!r}:{stop!r}"


def _split_or(s: str, sep: str, default: str = ":") -> tuple[str, str]:
    if sep not in s:
        return s, default
    return s.split(sep)
