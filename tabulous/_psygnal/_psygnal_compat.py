from __future__ import annotations

from types import MethodType
from typing import (
    Callable,
    Iterator,
    Any,
    TYPE_CHECKING,
    get_type_hints,
    Union,
    Type,
    NoReturn,
    cast,
)
from typing_extensions import get_args, get_origin
import warnings
import weakref
from contextlib import suppress, contextmanager
from functools import partial, lru_cache, reduce
import inspect
from inspect import Parameter, Signature, isclass
import threading

from psygnal import EmitLoopError


if TYPE_CHECKING:
    MethodRef = tuple[weakref.ReferenceType[object], str, Union[Callable, None]]
    NormedCallback = Union[MethodRef, Callable]
    StoredSlot = tuple[NormedCallback, Union[int, None]]
    ReducerFunc = Callable[[tuple, tuple], tuple]


# Following codes are mostly copied from psygnal (https://github.com/pyapp-kit/psygnal),
# except for the parametrized part. This file allows us to inherit signal objects.

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


_empty_signature = Signature()


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
