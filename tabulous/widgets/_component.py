from __future__ import annotations
import weakref
from typing import Generic, Literal, TYPE_CHECKING, TypeVar, overload

if TYPE_CHECKING:
    from typing_extensions import Self

T = TypeVar("T")


class _NoRef:
    """No reference."""


_no_ref = _NoRef()


class Component(Generic[T]):
    def __init__(self, parent: T | _NoRef = _no_ref):
        if parent is _no_ref:
            self._instances: dict[int, T] = {}
        else:
            self._instances = None
        self._parent_ref = weakref.ref(parent)

    @property
    def parent(self) -> T:
        """The parent object of this component."""
        out = self._parent_ref()
        if out is None:
            raise ReferenceError("Parent has been garbage collected.")
        return out

    def __repr__(self) -> str:
        return f"<{type(self).__name__} of {self.parent!r}>"

    @overload
    def __get__(self, obj: Literal[None], owner=None) -> Self[_NoRef]:
        ...

    @overload
    def __get__(self, obj: T, owner=None) -> Self[T]:
        ...

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        _id = id(obj)
        if (out := self._instances.get(_id)) is None:
            out = self._instances[_id] = self.__class__(obj)
        return out
