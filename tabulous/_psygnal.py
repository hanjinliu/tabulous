from __future__ import annotations

from types import MethodType
from typing import (
    Callable,
    Generic,
    overload,
    Any,
    TYPE_CHECKING,
    TypeVar,
    get_type_hints,
    Union,
)
from typing_extensions import get_args, get_origin, ParamSpec
import weakref
from contextlib import suppress
from functools import wraps, partial, lru_cache
from psygnal import Signal, SignalInstance, EmitLoopError
import inspect
from inspect import Parameter, Signature, isclass

from tabulous._range import RectRange, AnyRange, TableAnchorBase


__all__ = ["SignalArray"]

_P = ParamSpec("_P")
_R = TypeVar("_R")

if TYPE_CHECKING:
    MethodRef = tuple[weakref.ReferenceType[object], str, Union[Callable, None]]
    NormedCallback = Union[MethodRef, Callable]


class RangedSlot(Generic[_P, _R]):
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
        return f"RangedSlot<{self._func!r}>"

    @property
    def range(self) -> RectRange:
        """Slot range."""
        return self._range

    @property
    def func(self) -> Callable[_P, _R]:
        """The wrapped function."""
        return self._func


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

    def __getitem__(self, key) -> _SignalSubArrayRef:
        if isinstance(key, tuple):
            r, c = key
            key = RectRange(_parse_a_key(r), _parse_a_key(c))
        else:
            key = RectRange(_parse_a_key(key), slice(None))
        return _SignalSubArrayRef(self, key)

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
                slot.range.insert_rows(row, count)
        return None

    def insert_columns(self, col: int, count: int) -> None:
        """Insert columns and update slices in-place."""
        for slot, _ in self._slots:
            if isinstance(slot, RangedSlot):
                slot.range.insert_columns(col, count)
        return None

    def remove_rows(self, row: int, count: int):
        """Remove rows and update slices in-place."""
        to_be_disconnected: list[RangedSlot] = []
        for slot, _ in self._slots:
            if isinstance(slot, RangedSlot):
                slot.range.remove_rows(row, count)
                if slot.range.is_empty():
                    to_be_disconnected.append(slot)
        for slot in to_be_disconnected:
            self.disconnect(slot)
        return None

    def remove_columns(self, col: int, count: int):
        """Remove columns and update slices in-place."""
        to_be_disconnected: list[RangedSlot] = []
        for slot, _ in self._slots:
            if isinstance(slot, RangedSlot):
                slot.range.remove_columns(col, count)
                if slot.range.is_empty():
                    to_be_disconnected.append(slot)
        for slot in to_be_disconnected:
            self.disconnect(slot)
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
