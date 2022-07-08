from __future__ import annotations
import re
from typing import Any, TYPE_CHECKING
from psygnal import Signal, SignalGroup, SignalInstance
from psygnal.containers import EventedList

from .table import TableLayer

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


class TableList(EventedList[TableLayer]):
    events: NamedListEvents
    
    def __init__(self, parent: TableViewer):
        super().__init__()
        self.events = NamedListEvents()
        self._parent = parent

    def insert(self, index: int, table: TableLayer):
        if not isinstance(table, TableLayer):
            raise TypeError(f"Cannot insert {type(table)} to {self.__class__.__name__}.")
        
        table.name = self._coerce_name(table.name, except_for=table)
        @table.events.renamed.connect
        def _renamed_signal(name: str):
            coerced_name = self._coerce_name(name, table)
            table.name = coerced_name
            for i, tb in enumerate(self):
                if tb is table:
                    self.events.renamed.emit(i, coerced_name)
                    break
            return None
                    
        super().insert(index, table)
    
    def index(self, value: TableLayer | str, start: int = 0, stop: int = 999999) -> int:
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
    
    def get(self, name: str, default: Any | None = None) -> TableLayer | None:
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

    def _coerce_name(self, name: str, except_for: TableLayer):
        names = set(content.name for content in self if content is not except_for)
        
        suffix = re.findall(".*-(\d+)", name)
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
    
    def register_action(self, location: str):
        return self._parent._qwidget._tablist.registerAction(location)