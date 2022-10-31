from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    MutableMapping,
    TypeVar,
)
import weakref
from contextlib import contextmanager
import logging

import numpy as np
from ._selection_model import Index

if TYPE_CHECKING:
    import pandas as pd
    from .widgets import TableBase

logger = logging.getLogger("tabulous")


class Graph:
    """Calculation graph object that works in a table."""

    def __init__(
        self,
        table: TableBase,
        func: LiteralCallable,
        sources: list[tuple[slice, slice]],
        destination: tuple[slice, slice] | None = None,
    ):
        self._sources = sources
        self._destination = destination
        self._func = func
        self._table_ref = weakref.ref(table)
        self._callback_blocked = False

    def __hash__(self) -> int:
        return id(self)

    def __repr__(self) -> str:
        return f"Graph<{self.expr}>"

    @property
    def expr(self) -> str:
        """Get the graph expression in 'df.iloc[...] = ...' format."""
        if self._destination is None:
            expr = f"out = {self._func.expr}"
        else:
            rsl, csl = self._destination
            _r = _format_slice(rsl)
            _c = _format_slice(csl)
            expr = f"df.iloc[{_r}, {_c}] = {self._func.expr}"
        return expr

    @property
    def table(self) -> TableBase | None:
        """The parent table widget."""
        return self._table_ref()

    @property
    def destination(self) -> tuple[slice, slice] | None:
        return self._destination

    def set_pos(self, pos: tuple[int, int]):
        """Set the position of the graph origin."""
        self._func.set_pos(pos)
        return self

    @contextmanager
    def blocked(self):
        """Block the callback temporarily."""
        was_blocked = self._callback_blocked
        self._callback_blocked = True
        try:
            yield
        finally:
            self._callback_blocked = was_blocked

    def update(
        self,
    ):
        """Update the graph."""
        table = self.table
        if table is None:
            # garbage collected
            return self.disconnect()

        if not self._callback_blocked:
            with self.blocked():
                out = self._func()
                logger.debug(f"Running: {self.expr}")
                if (e := out.get_err()) and (sl := self._destination):
                    import pandas as pd

                    rsl, csl = sl
                    val = np.full(
                        (rsl.stop - rsl.start, csl.stop - csl.start),
                        repr(e),
                        dtype=object,
                    )
                    qtable_view = self.table._qwidget._qtable_view
                    with (
                        qtable_view._selection_model.blocked(),
                        qtable_view._ref_graphs.blocked(),
                    ):
                        table._qwidget.setDataFrameValue(rsl, csl, pd.DataFrame(val))
        else:
            out = None
        return out

    def initialize(self):
        """Initialize the graph object."""
        # First exception should be considered as a wrong expression.
        # Disconnect the callback.
        try:
            out = self.update()
        except Exception:
            self.disconnect()
            raise
        else:
            if isinstance(out, EvalResult):
                self._destination = out.range
        return self

    def connect(self):
        self.table.events.data.connect(self.update)
        logger.debug(f"Graph connected: {self.expr}")
        return self

    def disconnect(self):
        self.table.events.data.disconnect(self.update)
        logger.debug(f"Graph disconnected: {self.expr}")
        return self


class RectRange:
    def __init__(
        self,
        rsl: slice = slice(0, 0),
        csl: slice = slice(0, 0),
    ):
        self._rsl = rsl
        self._csl = csl

    def __contains__(self, other: Index):
        r, c = other
        rsl = self._rsl
        csl = self._csl
        return rsl.start <= r < rsl.stop and csl.start <= c < csl.stop


class AnyRange(RectRange):
    """Contains any indices."""

    def __contains__(self, item) -> bool:
        return True


class NoRange:
    """Contains no index."""

    def __contains__(self, item) -> bool:
        return False


_ANY_RANGE = AnyRange()
_NO_RANGE = NoRange()


class GraphManager(MutableMapping[Index, Graph]):
    """Calculation graph manager."""

    def __init__(self):
        self._graphs: dict[Index, Graph] = {}
        self._update_blocked = False
        self._blocked_ranges: RectRange = _NO_RANGE

    def __getitem__(self, key: Index) -> Graph:
        return self._graphs[key]

    def __setitem__(self, key: Index, graph: Graph) -> None:
        if key not in self._blocked_ranges:
            self.setitem_force(key, graph)

    def setitem_force(self, key: Index, graph: Graph) -> None:
        index = Index(*key)
        self.pop_force(index, None)
        self._graphs[index] = graph
        graph.connect()
        graph.initialize()
        logger.debug(f"Graph added at {key}")
        return None

    def __delitem__(self, key: Index) -> None:
        if key not in self._blocked_ranges:
            self.pop_force(key)

    __void = object()

    def pop_force(self, key: Index, default=__void) -> Graph:
        try:
            graph = self[key]
        except KeyError:
            if default is self.__void:
                raise
            return default
        else:
            graph.disconnect()
            del self._graphs[key]

            dst = graph.destination
            if dst:
                rsl, csl = dst
                area = (rsl.stop - rsl.start) * (csl.stop - csl.start)
                if area > 1:
                    logger.debug(f"Current graph pos {list(self.keys())}")
                    graph.table.selections = [dst]
                    graph.table._qwidget.deleteValues()
            logger.debug(f"Graph popped at {key}")
            return graph

    def __len__(self) -> int:
        return len(self._graphs)

    def __iter__(self):
        return iter(self._graphs)

    def is_all_blocked(self) -> bool:
        """True if manager update is disabled at any positions."""
        return self._blocked_ranges is _ANY_RANGE

    @contextmanager
    def blocked(self, *ranges):
        """Block graph updates in the given ranges temporarily."""
        old_range = self._blocked_ranges
        if len(ranges) == 0:
            ranges = _ANY_RANGE
        elif len(ranges) == 2:
            rsl, csl = ranges
            if isinstance(rsl, int):
                rsl = slice(rsl, rsl + 1)
            if isinstance(csl, int):
                csl = slice(csl, csl + 1)
            ranges = RectRange(rsl, csl)
        else:
            raise ValueError
        self._blocked_ranges = ranges
        try:
            yield
        finally:
            self._blocked_ranges = old_range

    def insert_rows(self, row: int, count: int):
        """Insert rows and update indices."""
        new_dict = {}
        for idx in list(self._graphs.keys()):
            if idx.row >= row:
                new_idx = Index(idx.row + count, idx.column)
                graph = self._graphs.pop(idx)
                new_dict[new_idx] = graph
                graph.set_pos(new_idx)

        self._graphs.update(new_dict)
        return None

    def insert_columns(self, col: int, count: int):
        """Insert columns and update indices."""
        new_dict = {}
        for idx in list(self._graphs.keys()):
            if idx.column >= col:
                new_idx = Index(idx.row, idx.column + count)
                graph = self._graphs.pop(idx)
                new_dict[new_idx] = graph
                graph.set_pos(new_idx)

        self._graphs.update(new_dict)
        return None

    def remove_rows(self, row: int, count: int):
        """Remove items that are in the given row range."""
        start = row
        stop = row + count
        for idx in list(self._graphs.keys()):
            if start <= idx.row < stop:
                self._graphs.pop(idx)

        return None

    def remove_columns(self, col: int, count: int):
        """Remove items that are in the given column range."""
        start = col
        stop = col + count
        for idx in list(self._graphs.keys()):
            if start <= idx.column < stop:
                self._graphs.pop(idx)

        return None


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

        logger.debug(f"Literal callable {expr} constructed at {pos}.")
        return LiteralCallable(expr, evaluator, pos)


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


def _format_slice(sl: slice) -> str:
    if sl == slice(None):
        return ":"
    return f"{sl.start}:{sl.stop}"
