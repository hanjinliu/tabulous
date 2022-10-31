from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    TypeVar,
)
from .._selection_model import Index

if TYPE_CHECKING:
    import pandas as pd
    from ..widgets import TableBase

_T = TypeVar("_T")


class LiteralCallable(Generic[_T]):
    """A callable object for eval."""

    def __init__(self, expr: str, func: Callable[[LiteralCallable], _T], pos: Index):
        self._expr = expr
        self._func = func
        self._pos = pos
        self._unblocked = False

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
                    _row, _col = _infer_slices(df, _out, _row, _col)
                elif out.size == 1:
                    _out = out.iloc[0, 0]
                else:
                    raise NotImplementedError("Cannot assign a DataFrame now.")

            elif isinstance(out, pd.Series):
                if out.shape == (1,):  # scalar
                    _out = out[0]
                else:  # update a column
                    _row, _col = _infer_slices(df, out, _row, _col)

            elif isinstance(out, np.ndarray):
                if out.ndim > 2:
                    raise ValueError("Cannot assign a >3D array.")
                _out = np.squeeze(out)
                if _out.ndim == 0:  # scalar
                    _out = qtable.convertValue(_row, _col, _out.item())
                elif _out.ndim == 1:  # 1D array
                    _row = slice(_row, _row + _out.shape[0])
                    _col = slice(_col, _col + 1)
                else:
                    _row = slice(_row, _row + _out.shape[0])
                    _col = slice(_col, _col + _out.shape[1])

            else:
                _out = qtable.convertValue(_row, _col, out)

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
            return EvalResult(out, (_row, _col))

        return LiteralCallable(expr, evaluator, pos)


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


def _infer_slices(
    df: pd.DataFrame,
    out: pd.Series,
    r: int,
    c: int,
) -> tuple[slice, slice]:
    """Infer how to concatenate ``out`` to ``df``."""

    #      x | x | x |
    #      x |(1)| x |(2)
    #      x | x | x |
    #     ---+---+---+---
    #        |(3)|   |(4)

    # 1. Return as a column vector for now.
    # 2. Return as a column vector.
    # 3. Return as a row vector.
    # 4. Cannot determine in which orientation results should be aligned. Raise Error.

    _nr, _nc = df.shape
    if _nc <= c:  # case 2, 4
        _orientation = "c"
    elif _nr <= r:  # case 3
        _orientation = "r"
    else:  # case 1
        _orientation = "infer"

    if _orientation == "infer":
        try:
            df.loc[:, out.index]
        except KeyError:
            try:
                df.loc[out.index, :]
            except KeyError:
                raise KeyError("Could not infer output orientation.")
            else:
                _orientation = "c"
        else:
            _orientation = "r"

    if _orientation == "r":
        rloc = slice(r, r + 1)
        istart = df.columns.get_loc(out.index[0])
        istop = df.columns.get_loc(out.index[-1]) + 1
        if (df.columns[istart:istop] == out.index).all():
            cloc = slice(istart, istop)
        else:
            raise ValueError("Output Series is not well sorted.")
    elif _orientation == "c":
        istart = df.index.get_loc(out.index[0])
        istop = df.index.get_loc(out.index[-1]) + 1
        if (df.index[istart:istop] == out.index).all():
            rloc = slice(istart, istop)
        else:
            raise ValueError("Output Series is not well sorted.")
        cloc = slice(c, c + 1)
    else:
        raise RuntimeError(_orientation)  # unreachable

    # check (r, c) is in the range
    if not (rloc.start <= r < rloc.stop and cloc.start <= c < cloc.stop):
        raise ValueError(
            f"The cell on editing {(r, c)} is not in the range of output "
            f"({rloc.start}:{rloc.stop}, {cloc.start}:{cloc.stop})."
        )
    return rloc, cloc
