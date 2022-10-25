from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Callable,
    Any,
    Generic,
    Hashable,
    MutableMapping,
    TypeVar,
)
import weakref
from contextlib import contextmanager

if TYPE_CHECKING:
    from qtpy.QtCore import pyqtBoundSignal
    import pandas as pd
    from typing_extensions import Self
    from .widgets import TableBase


class Graph:
    """Calculation graph object that works in a table."""

    def __init__(
        self,
        table: TableBase,
        func: Callable[[], Any],
        sources: list[tuple[slice, slice]],
    ):
        self._sources = sources
        self._func = func
        self._table_ref = weakref.ref(table)
        self._callback_blocked = False

    def __hash__(self) -> int:
        return id(self)

    @property
    def table(self) -> TableBase:
        return self._table_ref()

    @contextmanager
    def blocked(self):
        was_blocked = self._callback_blocked
        self._callback_blocked = True
        try:
            yield
        finally:
            self._callback_blocked = was_blocked

    def update(self):
        """Update the graph."""
        table = self.table
        if table is None:
            return self.disconnect()

        if not self._callback_blocked:
            with self.blocked():
                self._func()

        return None

    def connect(self):
        self.table.events.data.connect(self.update)
        # First exception should be considered as a wrong expression.
        # Disconnect the callback.
        try:
            self.update()
        except Exception:
            self.disconnect()
            raise
        return self

    def disconnect(self):
        self.table.events.data.disconnect(self.update)
        return self


_K = TypeVar("_K", bound=Hashable)


class GraphManager(MutableMapping[_K, Graph]):
    """Calculation graph manager."""

    def __init__(self):
        self._graphs: dict[_K, Graph] = {}
        self._update_blocked = False

    def __getitem__(self, key: _K) -> Graph:
        return self._graphs[key]

    def __setitem__(self, key: _K, value) -> None:
        if not self._update_blocked:
            self._graphs[key] = value

    def __delitem__(self, key: _K) -> None:
        if not self._update_blocked:
            del self._graphs[key]

    def __len__(self) -> int:
        return len(self._graphs)

    def __iter__(self):
        return iter(self._graphs)

    @contextmanager
    def blocked(self):
        was_blocked = self._update_blocked
        self._update_blocked = True
        try:
            yield
        finally:
            self._update_blocked = was_blocked


_T = TypeVar("_T")


class LiteralCallable(Generic[_T]):
    def __init__(self, expr: str, func: Callable[[], _T]):
        self._expr = expr
        self._func = func

    def __call__(self) -> _T:
        return self._func()

    @property
    def expr(self) -> str:
        return self._expr

    @classmethod
    def _from_table(
        cls: type[LiteralCallable],
        table: TableBase,
        expr: str,
        pos: tuple[int, int],
    ) -> LiteralCallable[EvalResult]:
        import numpy as np
        import pandas as pd

        qtable = table.native
        qtable_view = qtable._qtable_view
        qviewer = qtable_view.parentViewer()

        def evaluator():
            df = qtable.dataShown(parse=True)
            ns = qviewer._namespace.value()
            ns.update(df=df)
            try:
                out = eval(expr, ns, {})
            except Exception as e:
                return EvalResult(e)

            _row, _col = pos

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
                with qtable_view._selection_model.blocked(), qtable_view._ref_graphs.blocked():
                    qtable.setDataFrameValue(_row, _col, _out)

            elif isinstance(_row, int) and isinstance(_col, int):  # set scalar
                with qtable_view._selection_model.blocked(), qtable_view._ref_graphs.blocked():
                    qtable.setDataFrameValue(_row, _col, str(_out))

            else:
                raise RuntimeError(_row, _col)  # Unreachable
            return EvalResult(out)

        return LiteralCallable(expr, evaluator)


class EvalResult:
    def __init__(self, obj: Any):
        self._obj = obj

    @property
    def value(self) -> Any:
        return self._obj

    def unwrap(self) -> Any:
        obj = self._obj
        if isinstance(obj, Exception):
            raise obj
        return obj

    def get_err(self) -> Exception | None:
        if isinstance(self._obj, Exception):
            return self._obj
        return None


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
