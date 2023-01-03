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
    Type,
    NoReturn,
    cast,
)
from typing_extensions import get_args, get_origin, ParamSpec, Self
import warnings
import weakref
from contextlib import suppress, contextmanager
from functools import wraps, partial, lru_cache, reduce
import inspect
from inspect import Parameter, Signature, isclass
import threading
import numpy as np

from psygnal import EmitLoopError

from tabulous._range import RectRange, AnyRange, MultiRectRange, TableAnchorBase
from tabulous._selection_op import iter_extract_with_range
from tabulous.exceptions import UnreachableError

__all__ = ["SignalArray"]

logger = logging.getLogger(__name__)
_P = ParamSpec("_P")
_R = TypeVar("_R")

if TYPE_CHECKING:
    from tabulous.widgets._table import _DataFrameTableLayer
    import pandas as pd

    MethodRef = tuple[weakref.ReferenceType[object], str, Union[Callable, None]]
    NormedCallback = Union[MethodRef, Callable]
    StoredSlot = tuple[NormedCallback, Union[int, None]]
    ReducerFunc = Callable[[tuple, tuple], tuple]

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
        return self.eval_and_format(ns, ranges)[0]

    def eval_and_format(self, ns: dict[str, Any], ranges: MultiRectRange):
        expr = self.as_literal(ranges)
        logger.debug(f"About to run: {expr!r}")
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
    ):
        self._expr = expr
        super().__init__(lambda: self.call(), range)
        self._table = weakref.ref(table)
        self._last_destination: tuple[slice, slice] | None = None
        self._current_error: Exception | None = None
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
                _expr = f"df.iloc[{_fmt_slice(rsl)}, {_fmt_slice(csl)}] = {_expr}"
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
        self._source_pos = prx.get_source_index(pos[0]), pos[1]
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
        import pandas as pd

        table = self.table
        qtable = table._qwidget
        qtable_view = qtable._qtable_view
        qviewer = qtable.parentViewer()
        self._current_error = None

        df = qtable.getDataFrame()
        ns = dict(qviewer._namespace)
        ns.update(df=df)
        try:
            out, _expr = self._expr.eval_and_format(ns, self.range)
            logger.debug(f"Evaluated at {self.pos!r}")
        except Exception as e:
            logger.debug(f"Evaluation failed at {self.pos!r}: {e!r}")
            self._current_error = e
            return EvalResult(e, self.source_pos)

        _row, _col = self.source_pos

        _is_named_tuple = isinstance(out, tuple) and hasattr(out, "_fields")
        _is_dict = isinstance(out, dict)
        if _is_named_tuple or _is_dict:
            # fmt: off
            with qtable_view._selection_model.blocked(), \
                table.events.data.blocked(), \
                table.proxy.released():
                table.cell.set_labeled_data(_row, _col, out, sep=":")
            # fmt: on

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

        elif isinstance(out, (pd.Series, pd.Index)):
            if out.shape == (1,):  # scalar
                _out = out.values[0]
                _row, _col = self._infer_indices()
            else:  # update a column
                _out = out
                _row, _col = self._infer_slices(_out)

        elif isinstance(out, np.ndarray):
            _out = np.squeeze(out)
            if _out.size == 0:
                raise CellEvaluationError(
                    "Evaluation returned 0-sized array.", self.source_pos
                )
            if _out.ndim == 0:  # scalar
                _out = qtable.convertValue(_col, _out.item())
                _row, _col = self._infer_indices()
            elif _out.ndim == 1:  # 1D array
                _row, _col = self._infer_slices(_out)
            elif _out.ndim == 2:
                _row = slice(_row, _row + _out.shape[0])
                _col = slice(_col, _col + _out.shape[1])
            else:
                raise CellEvaluationError("Cannot assign a >3D array.", self.source_pos)

        else:
            _out = qtable.convertValue(_col, out)

        if isinstance(_row, slice) and isinstance(_col, slice):  # set 1D array
            _out = pd.DataFrame(out).astype(str)
            if _row.start == _row.stop - 1:  # row vector
                _out = _out.T

        elif isinstance(_row, int) and isinstance(_col, int):  # set scalar
            _out = str(_out)

        else:
            raise UnreachableError(type(_row), type(_col))

        _sel_model = qtable_view._selection_model
        # fmt: off
        with _sel_model.blocked(), \
            qtable_view._table_map.lock_pos(self.pos), \
            table.proxy.released(keep_widgets=True):
            qtable.setDataFrameValue(_row, _col, _out)
        # fmt: on
        self.last_destination = (_row, _col)
        return EvalResult(out, (_row, _col))

    def after_called(self, out: EvalResult) -> None:
        table = self.table
        qtable = table._qwidget
        qtable_view = qtable._qtable_view

        err = out.get_err()

        if err and (sl := self.last_destination):
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
            # fmt: off
            with qtable_view._selection_model.blocked(), \
                qtable_view._table_map.lock_pos(self.pos), \
                table.events.data.blocked(), \
                table.proxy.released(keep_widgets=True):
                table._qwidget.setDataFrameValue(rsl, csl, pd.DataFrame(val))
            # fmt: on
        return None

    def call(self):
        """Function that will be called when cells changed."""
        out = self.evaluate()
        self.after_called(out)
        return out

    def raise_in_msgbox(self) -> None:
        """Raise current error in a message box."""
        if self._current_error is None:
            raise ValueError("No error to raise.")
        from tabulous._qt._traceback import QtErrorMessageBox

        return QtErrorMessageBox.from_exc(self._current_error).exec_traceback()

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


_NULL = object()


class Signal:
    """Copy of psygnal.Signal, without mypyc compilation."""

    __slots__ = (
        "_name",
        "_signature",
        "description",
        "_check_nargs_on_connect",
        "_check_types_on_connect",
    )

    if TYPE_CHECKING:  # pragma: no cover
        _signature: Signature  # callback signature for this signal

    _current_emitter: SignalInstance | None = None

    def __init__(
        self,
        *types: Type[Any] | Signature,
        description: str = "",
        name: str | None = None,
        check_nargs_on_connect: bool = True,
        check_types_on_connect: bool = False,
    ) -> None:

        self._name = name
        self.description = description
        self._check_nargs_on_connect = check_nargs_on_connect
        self._check_types_on_connect = check_types_on_connect

        if types and isinstance(types[0], Signature):
            self._signature = types[0]
            if len(types) > 1:
                warnings.warn(
                    "Only a single argument is accepted when directly providing a"
                    f" `Signature`.  These args were ignored: {types[1:]}"
                )
        else:
            self._signature = _build_signature(*cast("tuple[Type[Any], ...]", types))

    @property
    def signature(self) -> Signature:
        """[Signature][inspect.Signature] supported by this Signal."""
        return self._signature

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        """Set name of signal when declared as a class attribute on `owner`."""
        if self._name is None:
            self._name = name

    def __getattr__(self, name: str) -> Any:
        """Get attribute. Provide useful error if trying to get `connect`."""
        if name == "connect":
            name = self.__class__.__name__
            raise AttributeError(
                f"{name!r} object has no attribute 'connect'. You can connect to the "
                "signal on the *instance* of a class with a Signal() class attribute. "
                "Or create a signal instance directly with SignalInstance."
            )
        return self.__getattribute__(name)

    def __get__(
        self, instance: Any, owner: Type[Any] | None = None
    ) -> Signal | SignalInstance:
        if instance is None:
            return self
        name = cast("str", self._name)
        signal_instance = SignalInstance(
            self.signature,
            instance=instance,
            name=name,
            check_nargs_on_connect=self._check_nargs_on_connect,
            check_types_on_connect=self._check_types_on_connect,
        )
        # instead of caching this signal instance on self, we just assign it
        # to instance.name ... this essentially breaks the descriptor,
        # (i.e. __get__ will never again be called for this instance, and we have no
        # idea how many instances are out there),
        # but it allows us to prevent creating a key for this instance (which may
        # not be hashable or weak-referenceable), and also provides a significant
        # speedup on attribute access (affecting everything).
        setattr(instance, name, signal_instance)
        return signal_instance

    @classmethod
    @contextmanager
    def _emitting(cls, emitter: SignalInstance) -> Iterator[None]:
        """Context that sets the sender on a receiver object while emitting a signal."""
        previous, cls._current_emitter = cls._current_emitter, emitter
        try:
            yield
        finally:
            cls._current_emitter = previous

    @classmethod
    def current_emitter(cls) -> SignalInstance | None:
        """Return currently emitting `SignalInstance`, if any.
        This will typically be used in a callback.
        Examples
        --------
        ```python
        from psygnal import Signal
        def my_callback():
            source = Signal.current_emitter()
        ```
        """
        return cls._current_emitter

    @classmethod
    def sender(cls) -> Any:
        """Return currently emitting object, if any.
        This will typically be used in a callback.
        """
        return getattr(cls._current_emitter, "instance", None)


_empty_signature = Signature()


class SignalInstance:
    """Copy of psygnal.SignalInstance, without mypyc compilation."""

    __slots__ = (
        "_signature",
        "_instance",
        "_name",
        "_slots",
        "_is_blocked",
        "_is_paused",
        "_args_queue",
        "_lock",
        "_check_nargs_on_connect",
        "_check_types_on_connect",
        "__weakref__",
    )

    def __init__(
        self,
        signature: Signature | tuple = _empty_signature,
        *,
        instance: Any = None,
        name: str | None = None,
        check_nargs_on_connect: bool = True,
        check_types_on_connect: bool = False,
    ) -> None:
        self._name = name
        self._instance: Any = instance
        self._args_queue: list[Any] = []  # filled when paused

        if isinstance(signature, (list, tuple)):
            signature = _build_signature(*signature)
        elif not isinstance(signature, Signature):  # pragma: no cover
            raise TypeError(
                "`signature` must be either a sequence of types, or an "
                "instance of `inspect.Signature`"
            )

        self._signature = signature
        self._check_nargs_on_connect = check_nargs_on_connect
        self._check_types_on_connect = check_types_on_connect
        self._slots: list[StoredSlot] = []
        self._is_blocked: bool = False
        self._is_paused: bool = False
        self._lock = threading.RLock()

    @property
    def signature(self) -> Signature:
        """Signature supported by this `SignalInstance`."""
        return self._signature

    @property
    def instance(self) -> Any:
        """Object that emits this `SignalInstance`."""
        return self._instance

    @property
    def name(self) -> str:
        """Name of this `SignalInstance`."""
        return self._name or ""

    def __repr__(self) -> str:
        """Return repr."""
        name = f" {self.name!r}" if self.name else ""
        instance = f" on {self.instance!r}" if self.instance is not None else ""
        return f"<{type(self).__name__}{name}{instance}>"

    def connect(
        self,
        slot: Callable | None = None,
        *,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
    ) -> Callable[[Callable], Callable] | Callable:
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

                self._slots.append((_normalize_slot(slot), max_args))
            return slot

        return _wrapper if slot is None else _wrapper(slot)

    def _check_nargs(
        self, slot: Callable, spec: Signature
    ) -> tuple[Signature | None, int | None]:
        """Make sure slot is compatible with signature.
        Also returns the maximum number of arguments that we can pass to the slot
        """
        try:
            slot_sig = _get_signature_possibly_qt(slot)
        except ValueError as e:
            warnings.warn(
                f"{e}. To silence this warning, connect with " "`check_nargs=False`"
            )
            return None, None
        minargs, maxargs = _acceptable_posarg_range(slot_sig)

        n_spec_params = len(spec.parameters)
        # if `slot` requires more arguments than we will provide, raise.
        if minargs > n_spec_params:
            extra = (
                f"- Slot requires at least {minargs} positional "
                f"arguments, but spec only provides {n_spec_params}"
            )
            self._raise_connection_error(slot, extra)
        _sig = None if isinstance(slot_sig, str) else slot_sig
        return _sig, maxargs

    def _raise_connection_error(self, slot: Callable, extra: str = "") -> NoReturn:
        name = getattr(slot, "__name__", str(slot))
        msg = f"Cannot connect slot {name!r} with signature: {signature(slot)}:\n"
        msg += extra
        msg += f"\n\nAccepted signature: {self.signature}"
        raise ValueError(msg)

    def _slot_index(self, slot: NormedCallback) -> int:
        """Get index of `slot` in `self._slots`.  Return -1 if not connected."""
        with self._lock:
            normed = _normalize_slot(slot)
            return next((i for i, s in enumerate(self._slots) if s[0] == normed), -1)

    def disconnect(
        self, slot: NormedCallback | None = None, missing_ok: bool = True
    ) -> None:
        with self._lock:
            if slot is None:
                # NOTE: clearing an empty list is actually a RuntimeError in Qt
                self._slots.clear()
                return

            idx = self._slot_index(slot)
            if idx != -1:
                self._slots.pop(idx)
                if isinstance(slot, PartialMethod):
                    _PARTIAL_CACHE.pop(id(slot), None)
                elif isinstance(slot, tuple) and callable(slot[2]):
                    _prune_partial_cache()
            elif not missing_ok:
                raise ValueError(f"slot is not connected: {slot}")

    def __contains__(self, slot: NormedCallback) -> bool:
        """Return `True` if slot is connected."""
        return self._slot_index(slot) >= 0

    def __len__(self) -> int:
        """Return number of connected slots."""
        return len(self._slots)

    def emit(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: bool = False,
    ) -> EmitThread | None:
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

        if asynchronous:
            sd = EmitThread(self, args)
            sd.start()
            return sd

        self._run_emit_loop(args)
        return None

    def __call__(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: bool = False,
    ) -> EmitThread | None:
        """Alias for `emit()`."""
        return self.emit(  # type: ignore
            *args,
            check_nargs=check_nargs,
            check_types=check_types,
            asynchronous=asynchronous,
        )

    def _run_emit_loop(self, args: tuple[Any, ...]) -> None:
        rem: list[NormedCallback] = []
        # allow receiver to query sender with Signal.current_emitter()
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

                    try:
                        cb(*args[:max_args])
                    except Exception as e:
                        raise EmitLoopError(
                            slot=slot, args=args[:max_args], exc=e
                        ) from e

            for slot in rem:
                self.disconnect(slot)

        return None

    def block(self) -> None:
        """Block this signal from emitting."""
        self._is_blocked = True

    def unblock(self) -> None:
        """Unblock this signal, allowing it to emit."""
        self._is_blocked = False

    @contextmanager
    def blocked(self) -> Iterator[None]:
        """Context manager to temporarily block this signal.
        Useful if you need to temporarily block all emission of a given signal,
        (for example, to avoid a recursive signal loop)
        Examples
        --------
        ```python
        class MyEmitter:
            changed = Signal()
            def make_a_change(self):
                self.changed.emit()
        obj = MyEmitter()
        with obj.changed.blocked()
            obj.make_a_change()  # will NOT emit a changed signal.
        ```
        """
        self.block()
        try:
            yield
        finally:
            self.unblock()

    def pause(self) -> None:
        """Pause all emission and collect *args tuples from emit().
        args passed to `emit` will be collected and re-emitted when `resume()` is
        called. For a context manager version, see `paused()`.
        """
        self._is_paused = True

    def resume(self, reducer: ReducerFunc | None = None, initial: Any = _NULL) -> None:
        """Resume (unpause) this signal, emitting everything in the queue.
        Parameters
        ----------
        reducer : Callable[[tuple, tuple], Any], optional
            If provided, all gathered args will be reduced into a single argument by
            passing `reducer` to `functools.reduce`.
            NOTE: args passed to `emit` are collected as tuples, so the two arguments
            passed to `reducer` will always be tuples. `reducer` must handle that and
            return an args tuple.
            For example, three `emit(1)` events would be reduced and re-emitted as
            follows: `self.emit(*functools.reduce(reducer, [(1,), (1,), (1,)]))`
        initial: any, optional
            intial value to pass to `functools.reduce`
        Examples
        --------
        >>> class T:
        ...     sig = Signal(int)
        >>> t = T()
        >>> t.sig.pause()
        >>> t.sig.emit(1)
        >>> t.sig.emit(2)
        >>> t.sig.emit(3)
        >>> t.sig.resume(lambda a, b: (a[0].union(set(b)),), (set(),))
        >>> # results in t.sig.emit({1, 2, 3})
        """
        self._is_paused = False
        # not sure why this attribute wouldn't be set, but when resuming in
        # EventedModel.update, it may be undefined (as seen in tests)
        if not getattr(self, "_args_queue", None):
            return
        if reducer is not None:
            if initial is _NULL:
                args = reduce(reducer, self._args_queue)
            else:
                args = reduce(reducer, self._args_queue, initial)
            self._run_emit_loop(args)
        else:
            for args in self._args_queue:
                self._run_emit_loop(args)
        self._args_queue.clear()

    @contextmanager
    def paused(
        self, reducer: ReducerFunc | None = None, initial: Any = _NULL
    ) -> Iterator[None]:
        """Context manager to temporarly pause this signal.
        Parameters
        ----------
        reducer : Callable[[tuple, tuple], Any], optional
            If provided, all gathered args will be reduced into a single argument by
            passing `reducer` to `functools.reduce`.
            NOTE: args passed to `emit` are collected as tuples, so the two arguments
            passed to `reducer` will always be tuples. `reducer` must handle that and
            return an args tuple.
            For example, three `emit(1)` events would be reduced and re-emitted as
            follows: `self.emit(*functools.reduce(reducer, [(1,), (1,), (1,)]))`
        initial: any, optional
            intial value to pass to `functools.reduce`
        Examples
        --------
        >>> with obj.signal.paused(lambda a, b: (a[0].union(set(b)),), (set(),)):
        ...     t.sig.emit(1)
        ...     t.sig.emit(2)
        ...     t.sig.emit(3)
        >>> # results in obj.signal.emit({1, 2, 3})
        """
        self.pause()
        try:
            yield
        finally:
            self.resume(reducer, initial)

    def __getstate__(self) -> dict:
        """Return dict of current state, for pickle."""
        d = {slot: getattr(self, slot) for slot in self.__slots__}
        d.pop("_lock", None)
        return d


class EmitThread(threading.Thread):
    """A thread to emit a signal asynchronously."""

    def __init__(self, signal_instance: SignalInstance, args: tuple[Any, ...]) -> None:
        super().__init__(name=signal_instance.name)
        self._signal_instance = signal_instance
        self.args = args
        # current = threading.currentThread()
        # self.parent = (current.getName(), current.ident)

    def run(self) -> None:
        """Run thread."""
        self._signal_instance._run_emit_loop(self.args)


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
                    logger.debug("Range became empty by removing rows")
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
                    logger.debug("Range became empty by removing columns")
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
    elif isinstance(k, (list, np.ndarray)):
        # fancy slicing, which occurs when the table is filtered/sorted.
        return slice(np.min(k), np.max(k) + 1)
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


def _fmt_slice(sl: slice) -> str:
    s0 = sl.start if sl.start is not None else ""
    s1 = sl.stop if sl.stop is not None else ""
    return f"{s0}:{s1}"


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


# #############################################################################
# #############################################################################


def _build_signature(*types: Type[Any]) -> Signature:
    params = [
        Parameter(name=f"p{i}", kind=Parameter.POSITIONAL_ONLY, annotation=t)
        for i, t in enumerate(types)
    ]
    return Signature(params)


def _normalize_slot(slot: Callable | NormedCallback) -> NormedCallback:
    if isinstance(slot, MethodType):
        return _get_method_name(slot) + (None,)
    if isinstance(slot, PartialMethod):
        return _partial_weakref(slot)
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


def _get_signature_possibly_qt(slot: Callable) -> Signature | str:
    # checking qt has to come first, since the signature of the emit method
    # of a Qt SignalInstance is just <Signature (*args: typing.Any) -> None>
    # https://bugreports.qt.io/browse/PYSIDE-1713
    sig = _guess_qtsignal_signature(slot)
    return signature(slot) if sig is None else sig


def _acceptable_posarg_range(
    sig: Signature | str, forbid_required_kwarg: bool = True
) -> tuple[int, int | None]:
    """Return tuple of (min, max) accepted positional arguments.
    Parameters
    ----------
    sig : Signature
        Signature object to evaluate
    forbid_required_kwarg : Optional[bool]
        Whether to allow required KEYWORD_ONLY parameters. by default True.
    Returns
    -------
    arg_range : Tuple[int, int]
        minimum, maximum number of acceptable positional arguments
    Raises
    ------
    ValueError
        If the signature has a required keyword_only parameter and
        `forbid_required_kwarg` is `True`.
    """
    if isinstance(sig, str):
        assert "(" in sig, f"Unrecognized string signature format: {sig}"
        inner = sig.split("(", 1)[1].split(")", 1)[0]
        minargs = maxargs = inner.count(",") + 1 if inner else 0
        return minargs, maxargs

    required = 0
    optional = 0
    posargs_unlimited = False
    _pos_required = {Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD}
    for param in sig.parameters.values():
        if param.kind in _pos_required:
            if param.default is Parameter.empty:
                required += 1
            else:
                optional += 1
        elif param.kind is Parameter.VAR_POSITIONAL:
            posargs_unlimited = True
        elif (
            param.kind is Parameter.KEYWORD_ONLY
            and param.default is Parameter.empty
            and forbid_required_kwarg
        ):
            raise ValueError("Required KEYWORD_ONLY parameters not allowed")
    return (required, None if posargs_unlimited else required + optional)


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


_PARTIAL_CACHE: dict[int, tuple[weakref.ref, str, Callable]] = {}


def _partial_weakref(slot_partial: PartialMethod) -> tuple[weakref.ref, str, Callable]:
    """For partial methods, make the weakref point to the wrapped object."""
    _id = id(slot_partial)

    # if the exact same partial is used twice, we don't want to recreate a new
    # wrap() function, because we want _partial_weakref(cb) == _partial_weakref(cb)
    # to be True.  So we cache the result of the first call using the id of the partial
    if _id not in _PARTIAL_CACHE:
        ref, name = _get_method_name(slot_partial.func)
        args_ = slot_partial.args
        kwargs_ = slot_partial.keywords

        def wrap(*args: Any, **kwargs: Any) -> Any:
            getattr(ref(), name)(*args_, *args, **kwargs_, **kwargs)

        _PARTIAL_CACHE[_id] = (ref, name, wrap)
    return _PARTIAL_CACHE[_id]


def _prune_partial_cache() -> None:
    """Remove any partial methods whose object has been garbage collected."""
    for key, (ref, *_) in list(_PARTIAL_CACHE.items()):
        if ref() is None:
            del _PARTIAL_CACHE[key]


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


def _guess_qtsignal_signature(obj: Any) -> str | None:
    """Return string signature if `obj` is a SignalInstance or Qt emit method.
    This is a bit of a hack, but we found no better way:
    https://stackoverflow.com/q/69976089/1631624
    https://bugreports.qt.io/browse/PYSIDE-1713
    """
    # on my machine, this takes ~700ns on PyQt5 and 8.7µs on PySide2
    type_ = type(obj)
    if "pyqtBoundSignal" in type_.__name__:
        return cast("str", obj.signal)
    qualname = getattr(obj, "__qualname__", "")
    if qualname == "pyqtBoundSignal.emit":
        return cast("str", obj.__self__.signal)
    if qualname == "SignalInstance.emit" and type_.__name__.startswith("builtin"):
        # we likely have the emit method of a SignalInstance
        # call it with ridiculous params to get the err
        return _ridiculously_call_emit(obj.__self__.emit)
    if "SignalInstance" in type_.__name__ and "QtCore" in getattr(
        type_, "__module__", ""
    ):
        return _ridiculously_call_emit(obj.emit)
    return None


_CRAZY_ARGS = (1,) * 255


def _ridiculously_call_emit(emitter: Any) -> str | None:
    """Call SignalInstance emit() to get the signature from err message."""
    try:
        emitter(*_CRAZY_ARGS)
    except TypeError as e:
        if "only accepts" in str(e):
            return str(e).split("only accepts")[0].strip()
    return None  # pragma: no cover
