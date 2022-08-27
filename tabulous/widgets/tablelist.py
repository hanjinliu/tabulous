from __future__ import annotations
import re
from typing import Any, TYPE_CHECKING, Callable, overload, TypeVar
from psygnal import Signal, SignalGroup, SignalInstance
from psygnal.containers import EventedList

from .table import TableBase

if TYPE_CHECKING:
    from .mainwindow import TableViewer

# Modified from psygnal/containers/_evented_list.py. See https://github.com/tlambert03/psygnal.
class NamedListEvents(SignalGroup):
    """Events available on EventedList.

    Attributes
    ----------
    inserting (index: int)
        emitted before an item is inserted at `index`
    inserted (index: int, value: Any)
        emitted after `value` is inserted at `index`
    removing (index: int)
        emitted before an item is removed at `index`
    removed (index: int, value: Any)
        emitted after `value` is removed at `index`
    moving (index: int, new_index: int)
        emitted before an item is moved from `index` to `new_index`
    moved (index: int, new_index: int, value: Any)
        emitted after `value` is moved from `index` to `new_index`
    changed (index: int or slice, old_value: Any or List[Any], value: Any or List[Any])
        emitted when `index` is set from `old_value` to `value`
    reordered (value: self)
        emitted when the list is reordered (eg. moved/reversed).
    child_event (index: int, object: Any, emitter: SignalInstance, args: tuple)
        emitted when an object in the list emits an event.
        Note that the EventedList must be created with `child_events=True` for this
        to be emitted.
    """

    inserting = Signal(int)  # idx
    inserted = Signal(int, object)  # (idx, value)
    removing = Signal(int)  # idx
    removed = Signal(int, object)  # (idx, value)
    moving = Signal(int, int)  # (src_idx, dest_idx)
    moved = Signal(tuple, object)  # ((src_idx, dest_idx), value)
    changed = Signal(object, object, object)  # (int | slice, old, new)
    reordered = Signal()
    child_event = Signal(int, object, SignalInstance, tuple)
    renamed = Signal(int, str)


_F = TypeVar("_F", bound=Callable)


class TableList(EventedList[TableBase]):
    events: NamedListEvents

    def __init__(self, parent: TableViewer):
        super().__init__()
        self.events = NamedListEvents()
        self._parent = parent
        self._install_contextmenu()

    def insert(self, index: int, table: TableBase):
        if not isinstance(table, TableBase):
            raise TypeError(
                f"Cannot insert {type(table)} to {self.__class__.__name__}."
            )

        table.name = self._coerce_name(table.name, except_for=table)

        @table.events.renamed.connect
        def _renamed_signal(name: str):
            coerced_name = self._coerce_name(name, table)
            with table.events.renamed.blocked():
                table.name = coerced_name
            for i, tb in enumerate(self):
                if tb is table:
                    self.events.renamed.emit(i, coerced_name)
                    break
            return None

        super().insert(index, table)

    def index(self, value: TableBase | str, start: int = 0, stop: int = 999999) -> int:
        """Override of list.index(), also accepts str input."""
        if isinstance(value, str):
            for i, content in enumerate(self):
                if content.name == value:
                    return i
            else:
                raise ValueError(f"No table named {value}")
        else:
            return super().index(value, start, stop)

    def rename(self, index_or_name: int | str, name: str) -> None:
        """Rename a table name."""
        table = self[index_or_name]
        name = self._coerce_name(name, except_for=table)
        table.name = name
        return None

    def get(self, name: str, default: Any | None = None) -> TableBase | None:
        """Get a table with name `name` if exists."""
        for content in self:
            if content.name == name:
                return content
        else:
            return default

    def __getitem__(self, key):
        if isinstance(key, str):
            key = self.index(key)
        return super().__getitem__(key)

    def __delitem__(self, key):
        if isinstance(key, str):
            key = self.index(key)
        return super().__delitem__(key)

    def _coerce_name(self, name: str, except_for: TableBase):
        names = {content.name for content in self if content is not except_for}

        suffix = re.findall(r".*-(\d+)", name)
        if suffix:
            suf = suffix[0]
            new_name = name
            name = new_name.rstrip(suf)[:-1]
            i = int(suffix[0])
        else:
            new_name = name
            i = 0
        while new_name in names:
            new_name = f"{name}-{i}"
            i += 1

        return new_name

    @overload
    def register_action(self, val: str) -> Callable[[_F], _F]:
        ...

    @overload
    def register_action(self, val: _F) -> _F:
        ...

    def register_action(self, val):
        """Register an contextmenu action to the tablelist."""
        if isinstance(val, str):
            return self._parent._qwidget._tablestack.registerAction(val)
        elif callable(val):
            location = val.__name__.replace("_", " ")
            return self._parent._qwidget._tablestack.registerAction(location)(val)
        else:
            raise ValueError("input must be a string or callable.")

    def tile(self, indices: list[int], orientation: str = "horizontal") -> None:
        """Tile the tables in the list."""
        self._parent._qwidget._tablestack.tileTables(indices, orientation=orientation)
        return None

    def untile(self, indices: int | list[int]):
        """Untile the tables in the list."""
        if isinstance(indices, int):
            indices = [indices]
        for idx in indices:
            self._parent._qwidget._tablestack.untileTable(idx)
        return None

    def _install_contextmenu(self):
        """Install the default contextmenu."""

        def view_mode_setter(mode: str):
            def _fset(index: int):
                self[index].view_mode = mode

            return _fset

        # fmt: off
        self.register_action("Copy all")(self._parent._qwidget._tablestack.copyData)
        self.register_action("Rename")(self._parent._qwidget._tablestack.enterEditingMode)
        self.register_action("Delete")(self.__delitem__)
        @self.register_action("Filter")
        def _filter(index: int):
            _main = self._parent._qwidget
            _main._tablestack.setCurrentIndex(index)
            _main._toolbar.filter()

        self.register_action("View>Horizontal dual view")(view_mode_setter("horizontal"))
        self.register_action("View>Vertical dual view")(view_mode_setter("vertical"))
        self.register_action("View>Popup view")(view_mode_setter("popup"))
        self.register_action("View>Reset view")(view_mode_setter("normal"))

        @self.register_action("Tile>Horizontal tiling")
        def _tile_h(index: int):
            if index == len(self) - 1:
                index -= 1
            self.tile([index, index + 1])

        @self.register_action("Tile>Vertical tiling")
        def _tile_v(index: int):
            if index == len(self) - 1:
                index -= 1
            self.tile([index, index + 1], orientation="vertical")

        @self.register_action("Tile>Untile")
        def _untile(index: int):
            self.untile(index)
        # fmt: on
