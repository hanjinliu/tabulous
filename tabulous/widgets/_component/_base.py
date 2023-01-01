from __future__ import annotations
import weakref
from typing import (
    Generic,
    Literal,
    TYPE_CHECKING,
    TypeVar,
    overload,
    Any,
)

if TYPE_CHECKING:
    from typing_extensions import Self
    from tabulous.widgets._table import TableBase, SpreadSheet
    from tabulous.widgets._mainwindow import TableViewerBase

T = TypeVar("T")


class _NoRef:
    """No reference."""


class Component(Generic[T]):
    _no_ref = _NoRef()

    def __init__(self, parent: T | _NoRef = _no_ref):
        if parent is self._no_ref:
            self._instances: dict[int, Self] = {}
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

    def __set__(self, obj: T, value: Any) -> None:
        if obj is None:
            raise AttributeError("Cannot set attribute.")
        _id = id(obj)
        if (ins := self._instances.get(_id)) is None:
            ins = self._instances[_id] = self.__class__(obj)

        return ins._set_value(value)

    def _set_value(self, value: Any):
        raise AttributeError("Cannot set attribute.")


class TableComponent(Component["TableBase"]):
    def _assert_spreadsheet(self) -> SpreadSheet:
        sheet = self.parent
        if sheet.table_type != "SpreadSheet":
            raise TypeError(
                f"{sheet.table_type!r} does not support insert. Use "
                "SpreadSheet instead."
            )
        return sheet


class ViewerComponent(Component["TableViewerBase"]):
    def show(self):
        """Show the component."""
        self.visible = True

    def hide(self):
        """Hide the component."""
        self.visible = False

    @property
    def visible(self) -> bool:
        """Visibility of the component."""
        raise NotImplementedError
