from __future__ import annotations
from abc import ABC, abstractmethod
import ast

import builtins
import logging
from typing import (
    Callable,
    Generic,
    Any,
    TYPE_CHECKING,
    TypeVar,
)
from typing_extensions import ParamSpec, Self
import weakref
from functools import wraps
import numpy as np
import pandas as pd

from tabulous._range import RectRange, AnyRange, MultiRectRange, TableAnchorBase
from tabulous._selection_op import iter_extract_with_range
from tabulous import _slice_op as _sl
from ._special_objects import RowCountGetter


logger = logging.getLogger(__name__)
_P = ParamSpec("_P")
_R = TypeVar("_R")

if TYPE_CHECKING:
    from tabulous.widgets._table import _DataFrameTableLayer


# "safe" builtin functions
# fmt: off
_BUILTINS = {
    k: getattr(builtins, k)
    for k in [
        "int", "str", "float", "bool", "list", "tuple", "set", "dict", "range",
        "slice", "frozenset", "len", "abs", "min", "max", "sum", "any", "all",
        "divmod", "id", "bin", "oct", "hex", "hash", "iter", "isinstance",
        "issubclass", "ord"
    ]
}
# fmt: on


class RangedSlot(Generic[_P, _R], TableAnchorBase):
    """
    Callable object tagged with response range.

    This object will be used in `SignalArray` to store the callback function.
    `range` indicates the range that the callback function will be called.
    """

    def __init__(self, func: Callable[_P, _R], range: RectRange = AnyRange()):
        if not callable(func):
            raise TypeError(f"func must be callable, not {type(func)}")
        if not isinstance(range, RectRange):
            raise TypeError("range must be a RectRange")
        self._func = func
        self._range = range
        wraps(func)(self)

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> Any:
        return self._func(*args, **kwargs)

    def __eq__(self, other: Any) -> bool:
        """Also return True if the wrapped function is the same."""
        if isinstance(other, RangedSlot):
            other = other._func
        return self._func == other

    def __repr__(self) -> str:
        clsname = type(self).__name__
        return f"{clsname}<{self._func!r}>"

    @property
    def range(self) -> RectRange:
        """Slot range."""
        return self._range

    @property
    def func(self) -> Callable[_P, _R]:
        """The wrapped function."""
        return self._func

    def insert_columns(self, col: int, count: int) -> None:
        """Insert columns and update range."""
        return self._range.insert_columns(col, count)

    def insert_rows(self, row: int, count: int) -> None:
        """Insert rows and update range."""
        return self._range.insert_rows(row, count)

    def remove_columns(self, col: int, count: int) -> None:
        """Remove columns and update range."""
        return self._range.remove_columns(col, count)

    def remove_rows(self, row: int, count: int) -> None:
        """Remove rows and update range."""
        return self._range.remove_rows(row, count)


class InCellExpr:
    SELECT = object()

    def __init__(self, objs: list):
        self._objs = objs

    def eval(self, ns: dict[str, Any], ranges: MultiRectRange):
        return self.eval_and_format(ns, ranges)[0]

    def eval_and_format(self, ns: dict[str, Any], ranges: MultiRectRange):
        expr = self.as_literal(ranges)
        logger.debug(f"About to run: {expr!r}")
        ns["__builtins__"] = _BUILTINS
        out = eval(expr, ns, {})
        return out, expr

    def as_literal(self, ranges: MultiRectRange) -> str:
        out: list[str] = []
        _it = iter(ranges)
        for o in self._objs:
            if o is self.SELECT:
                op = next(_it)
                out.append(op.as_iloc_string())
            else:
                out.append(o)
        return "".join(out)


class InCellRangedSlot(RangedSlot[_P, _R]):
    """A slot object with a reference to the table and position."""

    def __init__(
        self,
        expr: InCellExpr,
        pos: tuple[int, int],
        table: _DataFrameTableLayer,
        range: RectRange = AnyRange(),
        unlimited: tuple[bool, bool] = (False, False),
    ):
        self._expr = expr
        super().__init__(lambda: self.call(), range)
        self._table = weakref.ref(table)
        self._last_destination: tuple[slice, slice] | None = None
        self._last_destination_native: tuple[slice, slice] | None = None
        self._current_error: Exception | None = None
        self._unlimited = unlimited
        self.set_pos(pos)

    def __repr__(self) -> str:
        expr = self.as_literal()
        return f"{type(self).__name__}<{expr!r}>"

    def as_literal(self, dest: bool = False) -> str:
        """As a literal string that represents this slot."""
        _expr = self._expr.as_literal(self.range)
        if dest:
            if sl := self.last_destination:
                rsl, csl = sl
                if self._unlimited[0]:
                    rsl = slice(None)
                if self._unlimited[1]:
                    csl = slice(None)
                _expr = f"df.iloc[{_sl.fmt(rsl)}, {_sl.fmt(csl)}] = {_expr}"
            else:
                _expr = f"out = {_expr}"
        return _expr

    def format_error(self) -> str:
        """Format current exception as a string."""
        if self._current_error is None:
            return ""
        else:
            exc_type = type(self._current_error).__name__
            exc_msg = str(self._current_error)
            return f"{exc_type}: {exc_msg}"

    @property
    def table(self) -> _DataFrameTableLayer:
        """Get the parent table"""
        if table := self._table():
            return table
        raise RuntimeError("Table has been deleted.")

    @property
    def pos(self) -> tuple[int, int]:
        """The visual position of the cell that this slot is attached to."""
        return self._pos

    @property
    def source_pos(self) -> tuple[int, int]:
        """The source position of the cell that this slot is attached to."""
        return self._source_pos

    def set_pos(self, pos: tuple[int, int]):
        """Set the position of the cell that this slot is attached to."""
        self._pos = pos
        prx = self.table.proxy._get_proxy_object()
        cfil = self.table.columns.filter._get_filter()
        self._source_pos = (prx.get_source_index(pos[0]), cfil.get_source_index(pos[1]))
        return self

    @property
    def last_destination(self) -> tuple[slice, slice] | None:
        """The last range of results."""
        return self._last_destination

    @last_destination.setter
    def last_destination(self, val):
        if val is None:
            self._last_destination = None
        r, c = val
        if isinstance(r, int):
            r = slice(r, r + 1)
        if isinstance(c, int):
            c = slice(c, c + 1)
        self._last_destination = r, c

    @classmethod
    def from_table(
        cls: type[Self],
        table: _DataFrameTableLayer,
        expr: str,
        pos: tuple[int, int],
    ) -> Self:
        """Construct expression `expr` from `table` at `pos`."""
        qtable = table.native

        # normalize expression to iloc-slicing.
        df_ref = qtable._data_raw
        current_end = 0
        output: list[str] = []
        ranges: list[tuple[slice, slice]] = []
        row_unlimited = False
        col_unlimited = False
        for (start, end), op in iter_extract_with_range(expr):
            output.append(expr[current_end:start])
            output.append(InCellExpr.SELECT)
            cur_sl = op.as_iloc_slices(df_ref, fit_shape=False)
            if cur_sl[0] == slice(None):
                row_unlimited = True
            if cur_sl[1] == slice(None):
                col_unlimited = True
            ranges.append(cur_sl)
            current_end = end
        output.append(expr[current_end:])
        expr_obj = InCellExpr(output)
        # check if the expression contains `N`
        for ast_obj in ast.walk(ast.parse(expr)):
            if isinstance(ast_obj, ast.Name) and ast_obj.id == "N":
                # By this, this slot will be evaluated when the number of
                # columns changed.
                big = 99999999
                ranges.append((slice(big, big + 1), slice(None)))
                break
        # func pos range
        rng_obj = MultiRectRange.from_slices(ranges)
        unlimited = (row_unlimited, col_unlimited)
        return cls(expr_obj, pos, table, rng_obj, unlimited)

    def exception(self, msg: str):
        """Raise an evaluation error."""
        raise CellEvaluationError(msg, self.source_pos)

    def evaluate(self) -> EvalResult:
        """Evaluate expression, update cells and return the result."""
        table = self.table
        qtable = table._qwidget
        qtable_view = qtable._qtable_view
        qviewer = qtable.parentViewer()
        self._current_error = None

        df = qtable.getDataFrame()
        if qviewer is not None:
            ns = dict(qviewer._namespace)
        else:
            ns = {"np": np, "pd": pd}
        ns.update(df=df, N=RowCountGetter(qtable))
        try:
            out, _expr = self._expr.eval_and_format(ns, self.range)
            logger.debug(f"Evaluated at {self.pos!r}")
        except Exception as e:
            logger.debug(f"Evaluation failed at {self.pos!r}: {e!r}")
            self._current_error = e
            return EvalResult(e, self.source_pos)

        _is_named_tuple = isinstance(out, tuple) and hasattr(out, "_fields")
        _is_dict = isinstance(out, dict)
        if _is_named_tuple or _is_dict:
            _r, _c = self.source_pos
            # fmt: off
            with qtable_view._selection_model.blocked(), \
                table.events.data.blocked(), \
                table.proxy.released():
                table.cell.set_labeled_data(_r, _c, out, sep=":")
            # fmt: on
            self.last_destination = (slice(_r, _r + len(out)), slice(_c, _c + 1))
            self._unlimited = (False, False)
            return EvalResult(out, self.last_destination)

        if isinstance(out, pd.DataFrame):
            if out.shape[0] > 1 and out.shape[1] == 1:  # 1D array
                _out = out.iloc[:, 0]
                output = Array1DOutput(_out, *self._infer_slices(_out))
            elif out.size == 1:
                _out = out.iloc[0, 0]
                output = ScalarOutput(_out, *self._infer_indices())
            else:
                return self.exception("Cannot assign a DataFrame.")

        elif isinstance(out, (pd.Series, pd.Index)):
            if out.shape == (1,):  # scalar
                _out = out.values[0]
                output = ScalarOutput(_out, *self._infer_indices())
            else:  # update a column
                _out = np.asarray(out)
                output = Array1DOutput(_out, *self._infer_slices(_out))

        elif isinstance(out, np.ndarray):
            _out = np.squeeze(out)
            if _out.size == 0:
                return self.exception("Evaluation returned 0-sized array.")
            if _out.ndim == 0:  # scalar
                _out = qtable.convertValue(self.source_pos[1], _out.item())
                output = ScalarOutput(_out, *self._infer_indices())
            elif _out.ndim == 1:  # 1D array
                output = Array1DOutput(_out, *self._infer_slices(_out))
            elif _out.ndim == 2:
                _r, _c = self.source_pos
                _rsl = slice(_r, _r + _out.shape[0])
                _csl = slice(_c, _c + _out.shape[1])
                output = Array2DOutput(_out, _rsl, _csl)
            else:
                self.exception("Cannot assign a >3D array.")

        else:
            _r, _c = self.source_pos
            _out = qtable.convertValue(_c, out)
            output = ScalarOutput(_out, _r, _c)

        if isinstance(output, ScalarOutput):  # set scalar
            self._unlimited = (False, False)

        _sel_model = qtable_view._selection_model
        with (
            _sel_model.blocked(),
            qtable_view._table_map.lock_pos(self.pos),
            table.undo_manager.merging(lambda _: f"{self.as_literal(dest=True)}"),
            table.proxy.released(keep_widgets=True),
        ):
            if isinstance(output, ArrayOutput):
                key = output.get_sized_key()
            else:
                key = output.key
            qtable.setDataFrameValue(*key, output.value())
            qtable.model()._background_color_anim.start(*key)
        self.last_destination = key
        return EvalResult(out, output.key)

    def after_called(self, out: EvalResult) -> None:
        table = self.table
        qtable = table._qwidget
        qtable_view = qtable._qtable_view
        shape = qtable.dataShapeRaw()

        err = out.get_err()

        if err and (sl := self.last_destination):
            rsl, csl = sl
            # determine the error object
            if table.table_type == "SpreadSheet":
                err_repr = "#ERROR"
            else:
                err_repr = pd.NA

            val = np.full(
                (_sl.len_of(rsl, shape[0]), _sl.len_of(csl, shape[1])),
                err_repr,
                dtype=object,
            )
            # insert error values
            with (
                qtable_view._selection_model.blocked(),
                qtable_view._table_map.lock_pos(self.pos),
                table.events.data.blocked(),
                table.proxy.released(keep_widgets=True),
            ):
                qtable.setDataFrameValue(rsl, csl, pd.DataFrame(val))
                qtable.model()._background_color_anim.start(rsl, csl)
        return None

    def call(self):
        """Function that will be called when cells changed."""
        out = self.evaluate()
        self.after_called(out)
        return out

    def raise_in_msgbox(self, parent=None) -> None:
        """Raise current error in a message box."""
        if self._current_error is None:
            raise ValueError("No error to raise.")
        from tabulous._qt._traceback import QtErrorMessageBox

        return QtErrorMessageBox.from_exc(
            self._current_error, parent=parent
        ).exec_traceback()

    def insert_columns(self, col: int, count: int) -> None:
        """Insert columns and update range."""
        self._range.insert_columns(col, count)
        if dest := self.last_destination:
            rect = RectRange(*dest)
            rect.insert_columns(col, count)
            self.last_destination = rect.as_iloc()
        r, c = self.pos
        if c >= col:
            self.set_pos((r, c + count))

    def insert_rows(self, row: int, count: int) -> None:
        """Insert rows and update range."""
        self._range.insert_rows(row, count)
        if dest := self.last_destination:
            rect = RectRange(*dest)
            rect.insert_rows(row, count)
            self.last_destination = rect.as_iloc()
        r, c = self.pos
        if r >= row:
            self.set_pos((r + count, c))

    def remove_columns(self, col: int, count: int) -> None:
        """Remove columns and update range."""
        self._range.remove_columns(col, count)
        if dest := self.last_destination:
            rect = RectRange(*dest)
            rect.remove_columns(col, count)
            self.last_destination = rect.as_iloc()
        r, c = self.pos
        if c >= col:
            self.set_pos((r, c - count))

    def remove_rows(self, row: int, count: int) -> None:
        """Remove rows and update range."""
        self._range.remove_rows(row, count)
        r, c = self.pos
        if dest := self.last_destination:
            rect = RectRange(*dest)
            rect.remove_rows(row, count)
            self.last_destination = rect.as_iloc()
        if r >= row:
            self.set_pos((r - count, c))

    def _infer_indices(self) -> tuple[int, int]:
        """Infer how to concatenate a scalar to ``df``."""
        #  x | x | x |     1. Self-update is not safe. Raise Error.
        #  x |(1)| x |(2)  2. OK.
        #  x | x | x |     3. OK.
        # ---+---+---+---  4. Cannot determine in which orientation results should
        #    |(3)|   |(4)     be aligned. Raise Error.

        # Filter array selection.
        array_sels = list(self._range.iter_ranges())
        r, c = self.pos

        if len(array_sels) == 0:
            # if no array selection is found, return as a column vector.
            return r, c

        for rloc, cloc in array_sels:
            if _sl.in_range(r, rloc) and _sl.in_range(c, cloc):
                raise CellEvaluationError(
                    "Cell evaluation result overlaps with an array selection.",
                    pos=(r, c),
                )
        return r, c

    def _infer_slices(self, out: pd.Series | np.ndarray) -> tuple[slice, slice]:
        """Infer how to concatenate ``out`` to ``df``, based on the selections"""
        #  x | x | x |     1. Self-update is not safe. Raise Error.
        #  x |(1)| x |(2)  2. Return as a column vector.
        #  x | x | x |     3. Return as a row vector.
        # ---+---+---+---  4. Cannot determine in which orientation results should
        #    |(3)|   |(4)     be aligned. Raise Error.

        # Filter array selection.
        array_sels = list(self.range.iter_ranges())
        r, c = self.pos
        len_out = len(out)

        if len(array_sels) == 0:
            # if no array selection is found, return as a column vector.
            return slice(r, r + len_out), slice(c, c + 1)

        determined = None
        shape = self.table.native.dataShapeRaw()
        for rloc, cloc in array_sels:
            if _sl.len_1(rloc) and _sl.len_1(cloc) and determined is not None:
                continue

            if _sl.in_range(r, rloc):
                if _sl.in_range(c, cloc):
                    raise CellEvaluationError(
                        "Cell evaluation result overlaps with an array selection.",
                        pos=(r, c),
                    )
                else:
                    _r_len = _sl.len_of(rloc, shape[0])
                    if determined is None and len_out <= _r_len:
                        # column vector
                        if rloc.start is None and len_out == _r_len:
                            determined = (
                                slice(None),
                                slice(c, c + 1),
                            )
                        else:
                            rstart = 0 if rloc.start is None else rloc.start
                            determined = (
                                slice(rstart, rstart + len_out),
                                slice(c, c + 1),
                            )

            elif _sl.in_range(c, cloc):
                if determined is None and len_out <= _sl.len_of(cloc, shape[1]):
                    cstart: int = 0 if cloc.start is None else cloc.start
                    determined = (
                        slice(r, r + 1),
                        slice(cstart, cstart + len_out),
                    )  # row vector
            else:
                # cannot determine output positions, try next selection.
                pass

        if determined is None:
            raise CellEvaluationError(
                "Cell evaluation result is ambiguous. Could not determine the "
                "cells to write output.",
                pos=(r, c),
            )
        return determined


class CellEvaluationError(Exception):
    """Raised when cell evaluation is conducted in a wrong way."""

    def __init__(self, msg: str, pos: tuple[int, int]) -> None:
        super().__init__(msg)
        self._pos = pos


_T = TypeVar("_T")


class EvalResult(Generic[_T]):
    """A Rust-like Result type for evaluation."""

    def __init__(self, obj: _T | Exception, range: tuple[int | slice, int | slice]):
        self._obj = obj
        _r, _c = range
        if isinstance(_r, int):
            _r = slice(_r, _r + 1)
        if isinstance(_c, int):
            _c = slice(_c, _c + 1)
        self._range = (_r, _c)

    def __repr__(self) -> str:
        cname = type(self).__name__
        if isinstance(self._obj, Exception):
            desc = "Err"
        else:
            desc = "Ok"
        return f"{cname}<{desc}({self._obj!r})>"

    def _short_repr(self) -> str:
        cname = type(self).__name__
        if isinstance(self._obj, Exception):
            desc = "Err"
        else:
            desc = "Ok"
        _obj = repr(self._obj)
        if "\n" in _obj:
            _obj = _obj.split("\n")[0] + "..."
        if len(_obj.rstrip("...")) > 20:
            _obj = _obj[:20] + "..."
        return f"{cname}<{desc}({_obj})>"

    @property
    def range(self) -> tuple[slice, slice]:
        """Output range."""
        return self._range

    def unwrap(self) -> _T:
        obj = self._obj
        if isinstance(obj, Exception):
            raise obj
        return obj

    def get_err(self) -> Exception | None:
        if isinstance(self._obj, Exception):
            return self._obj
        return None

    def is_err(self) -> bool:
        """True is an exception is wrapped."""
        return isinstance(self._obj, Exception)


_Row = TypeVar("_Row")
_Col = TypeVar("_Col")


class Output(ABC, Generic[_T, _Row, _Col]):
    def __init__(self, obj: _T, row: _Row, col: _Col):
        self._obj = obj
        self._row = row
        self._col = col

    @property
    def obj(self) -> _T:
        return self._obj

    @property
    def row(self) -> _Row:
        return self._row

    @property
    def col(self) -> _Col:
        return self._col

    @property
    def key(self) -> tuple[_Row, _Col]:
        return self._row, self._col

    @abstractmethod
    def value(self) -> Any:
        """As a value that is ready for `setDataFrameValue`"""


class ScalarOutput(Output[Any, int, int]):
    def value(self) -> str:
        return str(self._obj)


class ArrayOutput(Output[_T, slice, slice]):
    def get_sized_key(self) -> tuple[slice, slice]:
        nr, nc = self.object_shape()
        if self._row.start is None:
            _row = slice(0, nr)
        else:
            _row = self._row
        if self._col.start is None:
            _col = slice(0, nc)
        else:
            _col = self._col
        return _row, _col

    @abstractmethod
    def object_shape(self) -> tuple[int, int]:
        """Shape of the object."""


class Array1DOutput(ArrayOutput["np.ndarray | pd.Series"]):
    def value(self) -> pd.DataFrame:
        _out = pd.DataFrame(self._obj).astype(str)
        if _sl.len_1(self._row):
            _out = _out.T
        return _out

    def object_shape(self) -> tuple[int, int]:
        return self._obj.shape[0], 1


class Array2DOutput(ArrayOutput["np.ndarray | pd.DataFrame"]):
    def value(self) -> pd.DataFrame:
        return pd.DataFrame(self._obj).astype(str)

    def object_shape(self) -> tuple[int, int]:
        return self._obj.shape
