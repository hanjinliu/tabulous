from __future__ import annotations
from functools import partial

from typing import (
    Any,
    Callable,
    Generic,
    TypeVar,
    Tuple,
    TYPE_CHECKING,
    overload,
    Literal,
)

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase, TableBase

_T = TypeVar("_T")
_U = TypeVar("_U")


class MockObject(Generic[_T]):
    def __init__(self, name: str = ""):
        self._name = name
        self._registered: list[_T] = []
        self._instances = {}

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if (out := self._instances.get(instance, None)) is None:
            out = self._instances[instance] = self.__class__(self._name)
        return out

    def __set_name__(self, owner, name):
        self._name = name

    def iter_registered(self):
        return iter(self._registered)


class ContextRegisterable(MockObject[Tuple[str, Callable]], Generic[_U]):
    # fmt: off
    @overload
    def register_action(self, loc: str, func: Literal[None] = None) -> Callable[[Callable[[_U, Any], None]], Callable[[_U, Any], None]]: ...  # noqa: E501
    @overload
    def register_action(self, loc: str, func: Callable[[_U, Any], None]) -> Callable[[_U, Any], None]: ...  # noqa: E501
    # fmt: on

    def register_action(self, loc, func=None):
        def wrapper(f):
            self._registered.append((loc, f))
            return f

        return wrapper(func) if func is not None else wrapper


class KeyMapMock(MockObject[Tuple[str, Callable]]):
    # fmt: off
    @overload
    def bind(self, key: str, func: Literal[None] = None) -> Callable[[Callable[[TableViewerBase, Any], None]], Callable[[TableViewerBase, Any], None]]: ...  # noqa: E501
    @overload
    def bind(self, key: str, func: Callable[[TableViewerBase, Any], None]) -> Callable[[TableViewerBase, Any], None]: ...  # noqa: E501
    # fmt: on

    def bind(self, key, func=None):
        def wrapper(f):
            self._registered.append((key, f))
            return f

        return wrapper(func) if func is not None else wrapper


class Initializer:
    _fields = ()

    def __hash__(self):
        return id(self)

    def join(self, other: Initializer):
        """Join initializers together."""
        for name in self._fields:
            self_field: MockObject = getattr(self, name)
            other_field: MockObject = getattr(other, name)
            self_field._registered.extend(other_field._registered)
        return self

    def wrap_args(self, args: tuple[Any, Callable], parent) -> tuple[Any, Callable]:
        arg, f = args
        f = partial(f, parent)
        return arg, f


class ViewerInitializer(Initializer):
    tables: ContextRegisterable[TableViewerBase] = ContextRegisterable("tables")
    keymap: ContextRegisterable[TableViewerBase] = KeyMapMock("keymap")

    _fields = ("tables", "keymap")

    def initializer_viewer(self, viewer: TableViewerBase):
        for args in self.tables.iter_registered():
            viewer.tables.register_action(*self.wrap_args(args, parent=viewer))
        for args in self.keymap.iter_registered():
            viewer.keymap.bind(*self.wrap_args(args, parent=viewer))


class TableInitializer(Initializer):
    cell: ContextRegisterable[TableBase] = ContextRegisterable("cell")
    index: ContextRegisterable[TableBase] = ContextRegisterable("index")
    columns: ContextRegisterable[TableBase] = ContextRegisterable("columns")

    _fields = ("cell", "index", "columns")

    def initializer_table(self, table: TableBase):
        for args in self.cell.iter_registered():
            table.cell.register_action(*self.wrap_args(args, parent=table))
        for args in self.index.iter_registered():
            table.index.register_action(*self.wrap_args(args, parent=table))
        for args in self.columns.iter_registered():
            table.columns.register_action(*self.wrap_args(args, parent=table))


def get_initializer() -> tuple[ViewerInitializer, TableInitializer]:
    return ViewerInitializer(), TableInitializer()
