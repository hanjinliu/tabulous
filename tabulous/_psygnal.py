from __future__ import annotations

from typing import Callable
import weakref
from psygnal import Signal, SignalInstance, EmitLoopError
from tabulous._range import RectRange
from inspect import Signature
from typing import overload, Any, Callable


class SignalArray(Signal):
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


class SignalArrayInstance(SignalInstance):
    def __init__(
        self,
        signature: Signature | tuple = _empty_signature,
        *,
        instance: Any = None,
        name: str | None = None,
        check_nargs_on_connect: bool = True,
        check_types_on_connect: bool = False,
    ) -> None:
        self._registry: list[tuple[RectRange, Callable]] = []
        super().__init__(
            signature,
            instance=instance,
            name=name,
            check_nargs_on_connect=check_nargs_on_connect,
            check_types_on_connect=check_types_on_connect,
        )

    def __getitem__(self, key):
        if isinstance(key, tuple):
            key = RectRange(_parse_a_key(key[0]), _parse_a_key(key[1]))
        else:
            key = RectRange(_parse_a_key(key), slice(None))
        return _SignalSubArrayRef(self, key)

    def _connect_at_range(self, range: RectRange, slot: Callable):
        """Connect a slot to the signal at a given range."""
        self._registry.append((range, slot))
        return slot

    def _emit_at_range(self, range: RectRange, *args, **kwargs):
        """Emit values at a given range."""
        for r, slot in self._registry:
            if range.includes(r):
                slot(*args, **kwargs)

    def _run_emit_loop(self, args: tuple[Any, ...]) -> None:
        rem = []
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


class _SignalSubArrayRef:
    def __init__(self, sig: SignalArrayInstance, key):
        self._sig = weakref.ref(sig)
        self._key = key

    def connect(self, slot: Callable):
        sig = self._sig()
        return sig._connect_at_range(self._key, slot)

    def emit(self, *args, **kwargs):
        sig = self._sig()
        return sig._emit_at_range(self._key, *args, **kwargs)


def _parse_a_key(k):
    if isinstance(k, slice):
        return k
    else:
        k = k.__index__()
        return slice(k, k + 1)
