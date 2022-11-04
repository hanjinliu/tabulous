from __future__ import annotations

import logging
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    Iterable,
    TypeVar,
)
from .._selection_model import Index
from .._selection_op import iter_extract, SelectionOperator

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd
    from ..widgets import TableBase

_T = TypeVar("_T")

logger = logging.getLogger("tabulous")


class CellEvaluationError(Exception):
    """Raised when cell evaluation is conducted in a wrong way."""

    def __init__(self, msg: str, pos: Index) -> None:
        super().__init__(msg)
        self._pos = pos


class LiteralCallable(Generic[_T]):
    """A callable object for eval."""

    def __init__(self, expr: str, func: Callable[[LiteralCallable], _T], pos: Index):
        self._expr = expr
        self._func = func
        self._pos = pos
        self._unblocked = False
        self._selection_ops = list(iter_extract(expr))
        self._last_destination: tuple[slice, slice] | None = None

    def __call__(self, unblock: bool = False) -> EvalResult[_T]:
        if unblock:
            self._unblocked = True
            try:
                out = self._func(self)
            finally:
                self._unblocked = False
            return out
        else:
            return self._func(self)

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self._expr}>"

    @property
    def expr(self) -> str:
        """The expression of the function."""
        return self._expr

    @property
    def pos(self) -> Index:
        return self._pos

    def set_pos(self, pos: tuple[int, int]):
        self._pos = Index(*pos)
        return self

    @property
    def selection_ops(self):
        """Return the list of selection operations."""
        return self._selection_ops

    @classmethod
    def from_table(
        cls: type[LiteralCallable],
        table: TableBase,
        expr: str,
        pos: tuple[int, int],
    ) -> LiteralCallable[EvalResult]:
        """Construct expression `expr` from `table` at `pos`."""
        import numpy as np
        import pandas as pd

        qtable = table.native
        qtable_view = qtable._qtable_view
        qviewer = qtable_view.parentViewer()

        def evaluator(_self: LiteralCallable):
            df = qtable.dataShown(parse=True)
            ns = dict(qviewer._namespace)
            ns.update(df=df)
            try:
                out = eval(expr, ns, {})
            except Exception as e:
                return EvalResult(e, _self.pos)

            _row, _col = _self.pos

            if isinstance(out, pd.DataFrame):
                if out.shape[0] > 1 and out.shape[1] == 1:  # 1D array
                    _out = out.iloc[:, 0]
                    _row, _col = _self._infer_slices(df, _out)
                elif out.size == 1:
                    _out = out.iloc[0, 0]
                    _row, _col = _self._infer_indices(df)
                else:
                    raise NotImplementedError("Cannot assign a DataFrame now.")

            elif isinstance(out, pd.Series):
                if out.shape == (1,):  # scalar
                    _out = out[0]
                    _row, _col = _self._infer_indices(df)
                else:  # update a column
                    _out = out
                    _row, _col = _self._infer_slices(df, _out)

            elif isinstance(out, np.ndarray):
                _out = np.squeeze(out)
                if _out.ndim == 0:  # scalar
                    _out = qtable.convertValue(_col, _out.item())
                    _row, _col = _self._infer_indices(df)
                elif _out.ndim == 1:  # 1D array
                    _row, _col = _self._infer_slices(df, _out)
                elif _out.ndim == 2:
                    _row = slice(_row, _row + _out.shape[0])
                    _col = slice(_col, _col + _out.shape[1])
                else:
                    raise CellEvaluationError("Cannot assign a >3D array.", Index(*pos))

            else:
                _out = qtable.convertValue(_col, out)

            if isinstance(_row, slice) and isinstance(_col, slice):  # set 1D array
                _out = pd.DataFrame(out).astype(str)
                if _row.start == _row.stop - 1:  # row vector
                    _out = _out.T

            elif isinstance(_row, int) and isinstance(_col, int):  # set scalar
                _out = str(_out)

            else:
                raise RuntimeError(_row, _col)  # Unreachable

            if not _self._unblocked:
                with (
                    qtable_view._selection_model.blocked(),
                    qtable_view._ref_graphs.blocked(*_self.pos),
                ):
                    qtable.setDataFrameValue(_row, _col, _out)
            else:
                with qtable_view._selection_model.blocked():
                    qtable.setDataFrameValue(_row, _col, _out)
            _self._last_destination = (_row, _col)
            return EvalResult(out, (_row, _col))

        return LiteralCallable(expr, evaluator, pos)

    def _infer_indices(self, df: pd.DataFrame) -> tuple[int, int]:
        """Infer how to concatenate a scalar to ``df``."""
        #  x | x | x |     1. Self-update is not safe. Raise Error.
        #  x |(1)| x |(2)  2. OK.
        #  x | x | x |     3. OK.
        # ---+---+---+---  4. Cannot determine in which orientation results should
        #    |(3)|   |(4)     be aligned. Raise Error.

        # Filter array selection.
        array_sels = _get_array_selections(self.selection_ops, df)
        r, c = self.pos

        if len(array_sels) == 0:
            # if no array selection is found, return as a column vector.
            return r, c

        for rloc, cloc in array_sels:
            in_r_range = rloc.start <= r < rloc.stop
            in_c_range = cloc.start <= c < cloc.stop

            if in_r_range and in_c_range:
                raise CellEvaluationError(
                    "Cell evaluation result overlaps with an array selection.",
                    pos=Index(r, c),
                )
        return r, c

    def _infer_slices(
        self, df: pd.DataFrame, out: pd.Series | np.ndarray
    ) -> tuple[slice, slice]:
        """Infer how to concatenate ``out`` to ``df``."""
        #  x | x | x |     1. Self-update is not safe. Raise Error.
        #  x |(1)| x |(2)  2. Return as a column vector.
        #  x | x | x |     3. Return as a row vector.
        # ---+---+---+---  4. Cannot determine in which orientation results should
        #    |(3)|   |(4)     be aligned. Raise Error.

        # Filter array selection.
        array_sels = _get_array_selections(self.selection_ops, df)
        r, c = self.pos
        len_out = len(out)

        if len(array_sels) == 0:
            # if no array selection is found, return as a column vector.
            return slice(r, r + len_out), slice(c, c + 1)

        determined = None
        for rloc, cloc in array_sels:
            in_r_range = rloc.start <= r < rloc.stop
            in_c_range = cloc.start <= c < cloc.stop
            r_len = rloc.stop - rloc.start
            c_len = cloc.stop - cloc.start

            if in_r_range:
                if in_c_range:
                    raise CellEvaluationError(
                        "Cell evaluation result overlaps with an array selection.",
                        pos=Index(r, c),
                    )
                else:
                    if determined is None and len_out <= r_len:
                        determined = (
                            slice(rloc.start, rloc.start + len_out),
                            slice(c, c + 1),
                        )  # column vector

            elif in_c_range:
                if determined is None and len_out <= c_len:
                    determined = (
                        slice(r, r + 1),
                        slice(cloc.start, cloc.start + len_out),
                    )  # row vector
            else:
                # cannot determine output positions, try next selection.
                pass

        if determined is None:
            raise CellEvaluationError(
                "Cell evaluation result is ambiguous. Could not determine the "
                "cells to write output.",
                pos=Index(r, c),
            )
        return determined


class EvalResult(Generic[_T]):
    """A Rust-like Result type for evaluation."""

    def __init__(self, obj: _T | Exception, range: tuple[int | slice, int | slice]):
        # TODO: range should be (int, int).
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


def _get_array_selections(selops: Iterable[SelectionOperator], df: pd.DataFrame):
    array_sels: list[tuple[slice, slice]] = []
    for selop in selops:
        sls = selop.as_iloc_slices(df)
        # append only if area > 1
        if sls[0].stop - sls[0].start > 1 or sls[1].stop - sls[1].start > 1:
            array_sels.append(sls)
    return array_sels
