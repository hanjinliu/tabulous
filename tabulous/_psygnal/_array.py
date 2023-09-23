from __future__ import annotations

import logging
from typing import (
    Callable,
    Iterator,
    Sequence,
    SupportsIndex,
    overload,
    Any,
    TYPE_CHECKING,
    Union,
)
import weakref
from inspect import Signature
import numpy as np

from psygnal import EmitLoopError

from tabulous._range import RectRange, AnyRange, MultiRectRange, TableAnchorBase
from ._psygnal_compat import (
    Signal,
    SignalInstance,
    _normalize_slot,
    _build_signature,
    _parameter_types_match,
    signature,
)
from ._slots import RangedSlot, InCellRangedSlot

__all__ = ["SignalArray"]

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    Slice1D = Union[SupportsIndex, slice]
    Slice2D = tuple[Slice1D, Slice1D]


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

    def _slot_index(self, slot: Any) -> int:
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
                        raise EmitLoopError(repr(slot), args[:max_args], e) from e

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
