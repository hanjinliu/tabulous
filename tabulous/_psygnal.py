from __future__ import annotations

from typing import Callable
import weakref
from psygnal import Signal, SignalInstance
from tabulous._range import RectRange


class SignalArrayInstance(SignalInstance):
    def __init__(self):
        self._registry: list[tuple[RectRange, Callable]] = []

    def __getitem__(self, key):
        if isinstance(key, tuple):
            key = RectRange(_parse_a_key(key[0]), _parse_a_key(key[1]))
        else:
            key = RectRange(_parse_a_key(key), slice(None))
        return _SignalSubArrayRef(self, key)

    def _connect_at_range(self, range: RectRange, slot: Callable):
        self._registry.append((range, slot))
        return slot

    def _emit_at_range(self, range: RectRange, *args, **kwargs):
        for r, slot in self._registry:
            if range.includes(r):
                slot(*args, **kwargs)


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
