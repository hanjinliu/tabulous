from __future__ import annotations

from typing import Callable, Generic, TypeVar, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase, TableBase

_T = TypeVar("_T")


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


class ContextRegisterable(MockObject[Tuple[str, Callable]]):
    def register_action(self, loc: str, func: Callable | None = None):
        def wrapper(f: Callable):
            self._registered.append((loc, f))
            return f

        return wrapper(func) if func is not None else wrapper


class KeyMapMock(MockObject[Tuple[str, Callable]]):
    def bind(self, *args):
        self._registered.append(args)


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


class ViewerInitializer(Initializer):
    tables = ContextRegisterable("tables")
    keymap = KeyMapMock("keymap")

    _fields = ("tables", "keymap")

    def initializer_viewer(self, viewer: TableViewerBase):
        for args in self.tables.iter_registered():
            viewer.tables.register_action(*args)
        for args in self.keymap.iter_registered():
            viewer.keymap.bind(*args)


class TableInitializer(Initializer):
    cell = ContextRegisterable("cell")
    index = ContextRegisterable("index")
    columns = ContextRegisterable("columns")

    _fields = ("cell", "index", "columns")

    def initializer_table(self, table: TableBase):
        for args in self.cell.iter_registered():
            table.cell.register_action(*args)
        for args in self.index.iter_registered():
            table.index.register_action(*args)
        for args in self.columns.iter_registered():
            table.columns.register_action(*args)


def get_initializer() -> tuple[ViewerInitializer, TableInitializer]:
    return ViewerInitializer(), TableInitializer()
