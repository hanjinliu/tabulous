from __future__ import annotations

from types import MethodType
import logging
from typing import (
    Callable,
    Generic,
    Iterator,
    Sequence,
    SupportsIndex,
    overload,
    Any,
    TYPE_CHECKING,
    TypeVar,
    get_type_hints,
    Union,
)
from typing_extensions import get_args, get_origin, ParamSpec, Self
import weakref
from contextlib import suppress
from functools import wraps, partial, lru_cache
from psygnal import Signal, SignalInstance, EmitLoopError
import inspect
from inspect import Parameter, Signature, isclass

from tabulous._range import RectRange, AnyRange, MultiRectRange, TableAnchorBase
from tabulous._selection_op import iter_extract_with_range, SelectionOperator

__all__ = ["SignalArray"]

logger = logging.getLogger(__name__)
_P = ParamSpec("_P")
_R = TypeVar("_R")

if TYPE_CHECKING:
    from tabulous.widgets import TableBase
    import numpy as np
    import pandas as pd

    MethodRef = tuple[weakref.ReferenceType[object], str, Union[Callable, None]]
    NormedCallback = Union[MethodRef, Callable]
    Slice1D = Union[SupportsIndex, slice]
    Slice2D = tuple[Slice1D, Slice1D]


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
        expr = self.as_literal(ranges)
        logger.debug(f"About to run: {expr!r}")
        return eval(expr, ns, {})

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
        table: TableBase,
        range: RectRange = AnyRange(),
    ):
        self._expr = expr
        super().__init__(lambda: self.call(), range)
        self._pos = pos
        self._table = weakref.ref(table)
        self._last_destination: tuple[slice, slice] | None = None

    def __repr__(self) -> str:
        expr = self.as_literal()
        return f"{type(self).__name__}<{expr!r}>"

    def as_literal(self) -> str:
        """As a literal string that represents this slot."""
        return self._expr.as_literal(self.range)

    @property
    def table(self) -> TableBase:
        """Get the parent table"""
        if table := self._table():
            return table
        raise RuntimeError("Table has been deleted.")

    @property
    def pos(self) -> tuple[int, int]:
        """The position of the cell that this slot is attached to."""
        return self._pos

    def set_pos(self, pos: tuple[int, int]):
        """Set the position of the cell that this slot is attached to."""
        self._pos = pos
        return self

    @property
    def last_destination(self) -> tuple[slice, slice] | None:
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
        table: TableBase,
        expr: str,
        pos: tuple[int, int],
    ) -> Self:
        """Construct expression `expr` from `table` at `pos`."""
        qtable = table.native

        # normalize expression to iloc-slicing.
        df_ref = qtable.dataShown(parse=False)
        current_end = 0
        output: list[str] = []
        ranges = []
        for (start, end), op in iter_extract_with_range(expr):
            output.append(expr[current_end:start])
            output.append(InCellExpr.SELECT)
            ranges.append(op.as_iloc_slices(df_ref))
            current_end = end
        output.append(expr[current_end:])
        expr_obj = InCellExpr(output)

        # func pos range
        return cls(expr_obj, pos, table, MultiRectRange.from_slices(ranges))

    def evaluate(self) -> EvalResult:
        """Evaluate expression, update cells and return the result."""
        import numpy as np
        import pandas as pd

        table = self.table
        qtable = table._qwidget
        qtable_view = qtable._qtable_view
        qviewer = qtable.parentViewer()

        df = qtable.dataShown(parse=True)
        ns = dict(qviewer._namespace)
        ns.update(df=df)
        try:
            out = self._expr.eval(ns, self.range)
            logger.debug(f"Evaluated at {self.pos!r}")
        except Exception as e:
            logger.debug(f"Evaluation failed at {self.pos!r}: {e!r}")
            return EvalResult(e, self.pos)

        _row, _col = self.pos

        _is_named_tuple = isinstance(out, tuple) and hasattr(out, "_fields")
        _is_dict = isinstance(out, dict)
        if _is_named_tuple or _is_dict:
            with qtable_view._selection_model.blocked(), table.events.data.blocked():
                table.cell.set_labeled_data(_row, _col, out, sep=":")

            self.last_destination = (
                slice(_row, _row + len(out)),
                slice(_col, _col + 1),
            )
            return EvalResult(out, (_row, _col))

        if isinstance(out, pd.DataFrame):
            if out.shape[0] > 1 and out.shape[1] == 1:  # 1D array
                _out = out.iloc[:, 0]
                _row, _col = self._infer_slices(_out)
            elif out.size == 1:
                _out = out.iloc[0, 0]
                _row, _col = self._infer_indices()
            else:
                raise NotImplementedError("Cannot assign a DataFrame now.")

        elif isinstance(out, pd.Series):
            if out.shape == (1,):  # scalar
                _out = out.values[0]
                _row, _col = self._infer_indices()
            else:  # update a column
                _out = out
                _row, _col = self._infer_slices(_out)

        elif isinstance(out, np.ndarray):
            _out = np.squeeze(out)
            if _out.size == 0:
                raise CellEvaluationError("Evaluation returned 0-sized array.")
            if _out.ndim == 0:  # scalar
                _out = qtable.convertValue(_col, _out.item())
                _row, _col = self._infer_indices()
            elif _out.ndim == 1:  # 1D array
                _row, _col = self._infer_slices(_out)
            elif _out.ndim == 2:
                _row = slice(_row, _row + _out.shape[0])
                _col = slice(_col, _col + _out.shape[1])
            else:
                raise CellEvaluationError("Cannot assign a >3D array.", self.pos)

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

        _sel_model = qtable_view._selection_model
        _rect = RectRange.new(*self.pos)
        with _sel_model.blocked(), qtable_view._table_map.lock_pos(self.pos):
            qtable.setDataFrameValue(_row, _col, _out)

        self.last_destination = (_row, _col)
        return EvalResult(out, (_row, _col))

    def after_called(self, out: EvalResult) -> None:
        table = self.table
        qtable = table._qwidget
        qtable_view = qtable._qtable_view

        if out.get_err() and (sl := self.last_destination):
            import pandas as pd

            rsl, csl = sl
            # determine the error object
            if table.table_type == "SpreadSheet":
                err_repr = "#ERROR"
            else:
                err_repr = pd.NA
            val = np.full(
                (rsl.stop - rsl.start, csl.stop - csl.start),
                err_repr,
                dtype=object,
            )
            with qtable_view._selection_model.blocked():
                with qtable_view._table_map.lock_pos(self.pos):
                    with table.events.data.blocked():
                        table._qwidget.setDataFrameValue(rsl, csl, pd.DataFrame(val))
        return None

    def call(self):
        """Function that will be called when cells changed."""
        out = self.evaluate()
        self.after_called(out)
        return out

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
            in_r_range = rloc.start <= r < rloc.stop
            in_c_range = cloc.start <= c < cloc.stop

            if in_r_range and in_c_range:
                raise CellEvaluationError(
                    "Cell evaluation result overlaps with an array selection.",
                    pos=(r, c),
                )
        return r, c

    def _infer_slices(self, out: pd.Series | np.ndarray) -> tuple[slice, slice]:
        """Infer how to concatenate ``out`` to ``df``."""
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
        for rloc, cloc in array_sels:
            in_r_range = rloc.start <= r < rloc.stop
            in_c_range = cloc.start <= c < cloc.stop
            r_len = rloc.stop - rloc.start
            c_len = cloc.stop - cloc.start

            if in_r_range:
                if in_c_range:
                    raise CellEvaluationError(
                        "Cell evaluation result overlaps with an array selection.",
                        pos=(r, c),
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
                pos=(r, c),
            )
        return determined


class CellEvaluationError(Exception):
    """Raised when cell evaluation is conducted in a wrong way."""

    def __init__(self, msg: str, pos: tuple[int, int]) -> None:
        super().__init__(msg)
        self._pos = pos


# Following codes are mostly copied from psygnal (https://github.com/pyapp-kit/psygnal),
# except for the parametrized part.


class SignalArray(Signal):
    """
    A 2D-parametric signal for a table widget.

    This class is an extension of `psygnal.Signal` that allows partial slot
    connection.

    ```python
    class MyEmitter:
        changed = SignalArray(int)

    emitter = MyEmitter()

    # Connect a slot to the whole table
    emitter.changed.connect(lambda arg: print(arg))
    # Connect a slot to a specific range of the table
    emitter.changed[0:5, 0:4].connect(lambda arg: print("partial:", arg))

    # Emit the signal
    emitter.changed.emit(1)
    # Emit the signal to a specific range
    emitter.changed[8, 8].emit(1)
    ```
    """

    @overload
    def __get__(
        self, instance: None, owner: type[Any] | None = None
    ) -> SignalArray:  # noqa
        ...  # pragma: no cover

    @overload
    def __get__(  # noqa
        self, instance: Any, owner: type[Any] | None = None
    ) -> SignalArrayInstance:
        ...  # pragma: no cover

    def __get__(self, instance: Any, owner: type[Any] | None = None):
        if instance is None:
            return self
        name = self._name
        signal_instance = SignalArrayInstance(
            self.signature,
            instance=instance,
            name=name,
            check_nargs_on_connect=self._check_nargs_on_connect,
            check_types_on_connect=self._check_types_on_connect,
        )
        setattr(instance, name, signal_instance)
        return signal_instance


_empty_signature = Signature()


class SignalArrayInstance(SignalInstance, TableAnchorBase):
    """Parametric version of `SignalInstance`."""

    def __init__(
        self,
        signature: Signature | tuple = _empty_signature,
        *,
        instance: Any = None,
        name: str | None = None,
        check_nargs_on_connect: bool = True,
        check_types_on_connect: bool = False,
    ) -> None:
        super().__init__(
            signature,
            instance=instance,
            name=name,
            check_nargs_on_connect=check_nargs_on_connect,
            check_types_on_connect=check_types_on_connect,
        )

    def __getitem__(self, key: Slice1D | Slice2D) -> _SignalSubArrayRef:
        """Return a sub-array reference."""
        _key = _parse_key(key)
        return _SignalSubArrayRef(self, _key)

    def mloc(self, keys: Sequence[Slice1D | Slice2D]) -> _SignalSubArrayRef:
        ranges = [_parse_key(key) for key in keys]
        return _SignalSubArrayRef(self, MultiRectRange(ranges))

    @overload
    def connect(
        self,
        *,
        check_nargs: bool | None = ...,
        check_types: bool | None = ...,
        unique: bool | str = ...,
        max_args: int | None = None,
        range: RectRange = ...,
    ) -> Callable[[Callable], Callable]:
        ...  # pragma: no cover

    @overload
    def connect(
        self,
        slot: Callable,
        *,
        check_nargs: bool | None = ...,
        check_types: bool | None = ...,
        unique: bool | str = ...,
        max_args: int | None = None,
        range: RectRange = ...,
    ) -> Callable:
        ...  # pragma: no cover

    def connect(
        self,
        slot: Callable | None = None,
        *,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        range: RectRange = AnyRange(),
    ):
        if check_nargs is None:
            check_nargs = self._check_nargs_on_connect
        if check_types is None:
            check_types = self._check_types_on_connect

        def _wrapper(slot: Callable, max_args: int | None = max_args) -> Callable:
            if not callable(slot):
                raise TypeError(f"Cannot connect to non-callable object: {slot}")

            with self._lock:
                if unique and slot in self:
                    if unique == "raise":
                        raise ValueError(
                            "Slot already connect. Use `connect(..., unique=False)` "
                            "to allow duplicate connections"
                        )
                    return slot

                slot_sig = None
                if check_nargs and (max_args is None):
                    slot_sig, max_args = self._check_nargs(slot, self.signature)
                if check_types:
                    slot_sig = slot_sig or signature(slot)
                    if not _parameter_types_match(slot, self.signature, slot_sig):
                        extra = f"- Slot types {slot_sig} do not match types in signal."
                        self._raise_connection_error(slot, extra)

                self._slots.append((_normalize_slot(RangedSlot(slot, range)), max_args))
            return slot

        return _wrapper if slot is None else _wrapper(slot)

    def connect_cell_slot(
        self,
        slot: InCellRangedSlot,
    ):
        with self._lock:
            _, max_args = self._check_nargs(slot, self.signature)
            self._slots.append((_normalize_slot(slot), max_args))
        return slot

    @overload
    def emit(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        range: RectRange = ...,
    ) -> None:
        ...  # pragma: no cover

    @overload
    def emit(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        range: RectRange = ...,
    ) -> None:
        ...  # pragma: no cover

    def emit(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        range: RectRange = AnyRange(),
    ) -> None:
        if self._is_blocked:
            return None

        if check_nargs:
            try:
                self.signature.bind(*args)
            except TypeError as e:
                raise TypeError(
                    f"Cannot emit args {args} from signal {self!r} with "
                    f"signature {self.signature}:\n{e}"
                ) from e

        if check_types and not _parameter_types_match(
            lambda: None, self.signature, _build_signature(*(type(a) for a in args))
        ):
            raise TypeError(
                f"Types provided to '{self.name}.emit' "
                f"{tuple(type(a).__name__ for a in args)} do not match signal "
                f"signature: {self.signature}"
            )

        if self._is_paused:
            self._args_queue.append(args)
            return None

        self._run_emit_loop(args, range)
        return None

    def insert_rows(self, row: int, count: int) -> None:
        """Insert rows and update slot ranges in-place."""
        for slot, _ in self._slots:
            if isinstance(slot, RangedSlot):
                slot.insert_rows(row, count)
        return None

    def insert_columns(self, col: int, count: int) -> None:
        """Insert columns and update slices in-place."""
        for slot, _ in self._slots:
            if isinstance(slot, RangedSlot):
                slot.insert_columns(col, count)
        return None

    def remove_rows(self, row: int, count: int):
        """Remove rows and update slices in-place."""
        to_be_disconnected: list[RangedSlot] = []
        for slot, _ in self._slots:
            if isinstance(slot, RangedSlot):
                slot.remove_rows(row, count)
                if slot.range.is_empty():
                    logger.debug(f"Range became empty by removing rows")
                    to_be_disconnected.append(slot)
        for slot in to_be_disconnected:
            self.disconnect(slot, missing_ok=False)
        return None

    def remove_columns(self, col: int, count: int):
        """Remove columns and update slices in-place."""
        to_be_disconnected: list[RangedSlot] = []
        for slot, _ in self._slots:
            if isinstance(slot, RangedSlot):
                slot.remove_columns(col, count)
                if slot.range.is_empty():
                    logger.debug(f"Range became empty by removing columns")
                    to_be_disconnected.append(slot)
        for slot in to_be_disconnected:
            self.disconnect(slot, missing_ok=False)
        return None

    def _slot_index(self, slot: NormedCallback) -> int:
        """Get index of `slot` in `self._slots`.  Return -1 if not connected."""
        with self._lock:
            if not isinstance(slot, RangedSlot):
                slot = RangedSlot(slot, AnyRange())
            normed = _normalize_slot(slot)
            return next((i for i, s in enumerate(self._slots) if s[0] == normed), -1)

    def _run_emit_loop(
        self,
        args: tuple[Any, ...],
        range: RectRange = AnyRange(),
    ) -> None:
        rem = []

        with self._lock:
            with Signal._emitting(self):
                for (slot, max_args) in self._slots:
                    if isinstance(slot, tuple):
                        _ref, name, method = slot
                        obj = _ref()
                        if obj is None:
                            rem.append(slot)  # add dead weakref
                            continue
                        if method is not None:
                            cb = method
                        else:
                            _cb = getattr(obj, name, None)
                            if _cb is None:  # pragma: no cover
                                rem.append(slot)  # object has changed?
                                continue
                            cb = _cb
                    else:
                        cb = slot

                    if isinstance(cb, RangedSlot) and not range.overlaps_with(cb.range):
                        continue
                    try:
                        cb(*args[:max_args])
                    except Exception as e:
                        raise EmitLoopError(
                            slot=slot, args=args[:max_args], exc=e
                        ) from e

            for slot in rem:
                self.disconnect(slot)

        return None

    def iter_slots(self) -> Iterator[Callable]:
        """Iterate over all connected slots."""
        for slot, _ in self._slots:
            if isinstance(slot, tuple):
                _ref, name, method = slot
                obj = _ref()
                if obj is None:
                    continue
                if method is not None:
                    cb = method
                else:
                    _cb = getattr(obj, name, None)
                    if _cb is None:
                        continue
                    cb = _cb
            else:
                cb = slot
            yield cb


class _SignalSubArrayRef:
    """A reference to a subarray of a signal."""

    def __init__(self, sig: SignalArrayInstance, key):
        self._sig: weakref.ReferenceType[SignalArrayInstance] = weakref.ref(sig)
        self._key = key

    def _get_parent(self) -> SignalArrayInstance:
        sig = self._sig()
        if sig is None:
            raise RuntimeError("Parent SignalArrayInstance has been garbage collected")
        return sig

    def connect(
        self,
        slot: Callable,
        *,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
    ):
        return self._get_parent().connect(
            slot,
            check_nargs=check_nargs,
            check_types=check_types,
            unique=unique,
            max_args=max_args,
            range=self._key,
        )

    def emit(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
    ):
        return self._get_parent().emit(
            *args, check_nargs=check_nargs, check_types=check_types, range=self._key
        )


def _parse_a_key(k):
    if isinstance(k, slice):
        return k
    else:
        k = k.__index__()
        return slice(k, k + 1)


def _parse_key(key):
    if isinstance(key, tuple):
        if len(key) == 2:
            r, c = key
            key = RectRange(_parse_a_key(r), _parse_a_key(c))
        elif len(key) == 1:
            key = RectRange(_parse_a_key(key[0]))
        else:
            raise IndexError("too many indices")
    else:
        key = RectRange(_parse_a_key(key), slice(None))
    return key


_T = TypeVar("_T")


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


class PartialMethodMeta(type):
    def __instancecheck__(cls, inst: object) -> bool:
        return isinstance(inst, partial) and isinstance(inst.func, MethodType)


class PartialMethod(metaclass=PartialMethodMeta):
    """Bound method wrapped in partial: `partial(MyClass().some_method, y=1)`."""

    func: MethodType
    args: tuple
    keywords: dict[str, Any]


def signature(obj: Any) -> inspect.Signature:
    try:
        return inspect.signature(obj)
    except ValueError as e:
        with suppress(Exception):
            if not inspect.ismethod(obj):
                return _stub_sig(obj)
        raise e from e


@lru_cache(maxsize=None)
def _stub_sig(obj: Any) -> Signature:
    import builtins

    if obj is builtins.print:
        params = [
            Parameter(name="value", kind=Parameter.VAR_POSITIONAL),
            Parameter(name="sep", kind=Parameter.KEYWORD_ONLY, default=" "),
            Parameter(name="end", kind=Parameter.KEYWORD_ONLY, default="\n"),
            Parameter(name="file", kind=Parameter.KEYWORD_ONLY, default=None),
            Parameter(name="flush", kind=Parameter.KEYWORD_ONLY, default=False),
        ]
        return Signature(params)
    raise ValueError("unknown object")


def _build_signature(*types: type[Any]) -> Signature:
    params = [
        Parameter(name=f"p{i}", kind=Parameter.POSITIONAL_ONLY, annotation=t)
        for i, t in enumerate(types)
    ]
    return Signature(params)


def _normalize_slot(slot: Callable | NormedCallback) -> NormedCallback:
    if isinstance(slot, MethodType):
        return _get_method_name(slot) + (None,)
    if isinstance(slot, PartialMethod):
        raise NotImplementedError()
    if isinstance(slot, tuple) and not isinstance(slot[0], weakref.ref):
        return (weakref.ref(slot[0]), slot[1], slot[2])
    return slot


# def f(a, /, b, c=None, *d, f=None, **g): print(locals())
#
# a: kind=POSITIONAL_ONLY,       default=Parameter.empty    # 1 required posarg
# b: kind=POSITIONAL_OR_KEYWORD, default=Parameter.empty    # 1 requires posarg
# c: kind=POSITIONAL_OR_KEYWORD, default=None               # 1 optional posarg
# d: kind=VAR_POSITIONAL,        default=Parameter.empty    # N optional posargs
# e: kind=KEYWORD_ONLY,          default=Parameter.empty    # 1 REQUIRED kwarg
# f: kind=KEYWORD_ONLY,          default=None               # 1 optional kwarg
# g: kind=VAR_KEYWORD,           default=Parameter.empty    # N optional kwargs


def _parameter_types_match(
    function: Callable, spec: Signature, func_sig: Signature | None = None
) -> bool:
    """Return True if types in `function` signature match those in `spec`.

    Parameters
    ----------
    function : Callable
        A function to validate
    spec : Signature
        The Signature against which the `function` should be validated.
    func_sig : Signature, optional
        Signature for `function`, if `None`, signature will be inspected.
        by default None

    Returns
    -------
    bool
        True if the parameter types match.
    """
    fsig = func_sig or signature(function)

    func_hints = None
    for f_param, spec_param in zip(fsig.parameters.values(), spec.parameters.values()):
        f_anno = f_param.annotation
        if f_anno is fsig.empty:
            # if function parameter is not type annotated, allow it.
            continue

        if isinstance(f_anno, str):
            if func_hints is None:
                func_hints = get_type_hints(function)
            f_anno = func_hints.get(f_param.name)

        if not _is_subclass(f_anno, spec_param.annotation):
            return False
    return True


def _is_subclass(left: type[Any], right: type) -> bool:
    """Variant of issubclass with support for unions."""
    if not isclass(left) and get_origin(left) is Union:
        return any(issubclass(i, right) for i in get_args(left))
    return issubclass(left, right)


def _get_method_name(slot: MethodType) -> tuple[weakref.ref, str]:
    obj = slot.__self__
    # some decorators will alter method.__name__, so that obj.method
    # will not be equal to getattr(obj, obj.method.__name__).
    # We check for that case here and find the proper name in the function's closures
    if getattr(obj, slot.__name__, None) != slot:
        for c in slot.__closure__ or ():
            cname = getattr(c.cell_contents, "__name__", None)
            if cname and getattr(obj, cname, None) == slot:
                return weakref.ref(obj), cname
        # slower, but catches cases like assigned functions
        # that won't have function in closure
        for name in reversed(dir(obj)):  # most dunder methods come first
            if getattr(obj, name) == slot:
                return weakref.ref(obj), name
        # we don't know what to do here.
        raise RuntimeError(  # pragma: no cover
            f"Could not find method on {obj} corresponding to decorated function {slot}"
        )
    return weakref.ref(obj), slot.__name__
