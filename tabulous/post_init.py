from __future__ import annotations

from typing import (
    Any,
    Callable,
    Generic,
    Hashable,
    TypeVar,
    TYPE_CHECKING,
    overload,
    Literal,
)

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase, TableBase
    from typing_extensions import Self

_T = TypeVar("_T")


class _Joinable:
    def __init__(self, name: str = ""):
        self._name = name
        self._instances: dict[Hashable, Self] = {}

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if (out := self._instances.get(instance, None)) is None:
            out = self._instances[instance] = self.__class__(self._name)
        return out

    def __set_name__(self, owner, name):
        self._name = name

    def _join(self, other: Self):
        raise NotImplementedError()


class _Registerable(_Joinable):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self._registered: list[Any] = []

    def _register(self, loc, func=None):
        def wrapper(f):
            self._registered.append((loc, f))
            return f

        return wrapper(func) if func is not None else wrapper

    def _join(self, other: Self):
        self._registered.extend(other._registered)


class _Updatable(_Joinable):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self._dict = {}

    def __setitem__(self, key: str, value: Any):
        self._dict[key] = value

    def update(self, *args, **kwargs):
        self._dict.update(*args, **kwargs)

    def add(self, obj: _T) -> _T:
        """A decorator to add an callable object to the namespace."""
        if callable(obj) or isinstance(obj, type):
            name = obj.__name__
            self[name] = obj
        else:
            raise TypeError(f"Expected to be used as a decorator, got {type(obj)}")
        return obj

    def _join(self, other: Self):
        self._dict.update(other._dict)


class ContextRegisterable(_Registerable, Generic[_T]):
    """A mock for the `register` method."""

    # fmt: off
    @overload
    def register(self, loc: str, func: Literal[None] = None) -> Callable[[Callable[[_T, Any], None]], Callable[[_T, Any], None]]: ...  # noqa: E501
    @overload
    def register(self, loc: str, func: Callable[[_T, Any], None]) -> Callable[[_T, Any], None]: ...  # noqa: E501
    # fmt: on

    def register(self, loc, func=None):
        return self._register(loc, func)


class KeyMapMock(_Registerable):
    """A mock for the `keymap` attribute of a table viewer instance."""

    # fmt: off
    @overload
    def register(self, key: str, func: Literal[None] = None) -> Callable[[Callable[[TableViewerBase, Any], None]], Callable[[TableViewerBase, Any], None]]: ...  # noqa: E501
    @overload
    def register(self, key: str, func: Callable[[TableViewerBase, Any], None]) -> Callable[[TableViewerBase, Any], None]: ...  # noqa: E501
    # fmt: on

    def register(self, key, func=None):
        return self._register(key, func)


class CellNamespaceMock(_Updatable):
    """A mock for the `cell_namespace` attribute of a table viewer instance."""


class ConsoleMock(_Updatable):
    """A mock for the `console` attribute of a table viewer instance."""


class CommandPaletteMock(_Registerable):
    # fmt: off
    @overload
    def register(self, command: Callable[[TableViewerBase], Any], title: str, desc: str | None, key: str | None): ...  # noqa: E501
    @overload
    def register(self, command: Literal[None], title: str, desc: str | None, key: str | None): ...  # noqa: E501
    # fmt: on

    def register(self, command, title="User defined", desc=None, key=None):
        return self._register((command, title, desc, key))


class Initializer:
    _fields = ()

    def __hash__(self):
        return id(self)

    def join(self, other: Initializer):
        """Join initializers together."""
        for name in self._fields:
            self_field: _Registerable = getattr(self, name)
            other_field: _Registerable = getattr(other, name)
            self_field._join(other_field)
        return self


class ViewerInitializer(Initializer):
    tables: ContextRegisterable[TableViewerBase] = ContextRegisterable()
    keymap: ContextRegisterable[TableViewerBase] = KeyMapMock()
    console: ConsoleMock[TableViewerBase] = ConsoleMock()
    cell_namespace: CellNamespaceMock[TableViewerBase] = CellNamespaceMock()
    command_palette: CommandPaletteMock[TableViewerBase] = CommandPaletteMock()

    _fields = ("tables", "keymap", "console", "cell_namespace", "command_palette")

    def initialize_viewer(self, viewer: TableViewerBase):
        for args in self.tables._registered:
            viewer.tables.register(*args)
        for args in self.keymap._registered:
            # NOTE: The QtKeyMap object is currently a class variable. When the second
            # viewer is launched, old keybindings are still registered. To avoid this,
            # we just allow overwriting the keymap.
            viewer.keymap.register(*args, overwrite=True)
        viewer.cell_namespace.update_safely(self.cell_namespace._dict)
        viewer.console.update(self.console._dict)
        for args in self.command_palette._registered:
            viewer.command_palette.register(*args)


class TableInitializer(Initializer):
    cell: ContextRegisterable[TableBase] = ContextRegisterable()
    index: ContextRegisterable[TableBase] = ContextRegisterable()
    columns: ContextRegisterable[TableBase] = ContextRegisterable()
    keymap: ContextRegisterable[TableBase] = KeyMapMock()

    _fields = ("cell", "index", "columns", "keymap")

    def initialize_table(self, table: TableBase):
        for args in self.cell._registered:
            table.cell.register(*args)
        for args in self.index._registered:
            table.index.register(*args)
        for args in self.columns._registered:
            table.columns.register(*args)
        for args in self.keymap._registered:
            table.keymap.register(*args, overwrite=True)


_VIEWER_INITIALIZER = ViewerInitializer()
_TABLE_INITIALIZER = TableInitializer()


def get_initializers() -> tuple[ViewerInitializer, TableInitializer]:
    """Get viewer and table initializers."""
    return _VIEWER_INITIALIZER, _TABLE_INITIALIZER
