from __future__ import annotations
from functools import partial
from pathlib import Path
import weakref
from typing import TYPE_CHECKING
from psygnal import Signal, SignalGroup

from .._qt import QMainWindow, get_app

from .table import TableLayer
from .tablelist import TableList

if TYPE_CHECKING:
    from .._qt._dockwidget import QtDockWidget
    from qtpy.QtWidgets import QWidget
    from magicgui.widgets import Widget
    
class TableViewerSignal(SignalGroup):
    current_index = Signal(int)

class TableViewer:
    events: TableViewerSignal
    _dock_widgets: weakref.WeakValueDictionary[str, QtDockWidget]
    
    def __init__(self, *, show: bool = True):
        app = get_app()
        self._qwidget = QMainWindow()
        self._qwidget._table_viewer = self
        self._tablist = TableList(parent=self)
        self._tablist.events.inserted.connect(self._link_renamed_signals)
        self._tablist.events.removed.connect(self._remove_backend_table)
        self._tablist.events.moved.connect(self._move_backend_widget)
        self._qwidget._tablist.itemMoved.connect(self._move_table)
        self._qwidget._tablestack.dropped.connect(self.open)
        
        self._dock_widgets = weakref.WeakValueDictionary()
        
        self._tablist.events.inserted.connect(self.reset_choices)
        self._tablist.events.removed.connect(self.reset_choices)
        self._tablist.events.moved.connect(self.reset_choices)
        self._tablist.events.changed.connect(self.reset_choices)
        
        self.events = TableViewerSignal()
        
        if show:
            self.show()
    
    def _move_table(self, src: int, dst: int):
        """Move evented list when list is moved in GUI."""
        with self._tablist.events.blocked():
            self._tablist.move(src, dst)
            self._qwidget._tablestack.moveWidget(src, dst)
        self._qwidget._tablestack.setCurrentIndex(dst)
    
    def _move_backend_widget(self, src: int, dst: int):
        """Move backend tab list widget when programmatically moved."""
        self._qwidget._tablist.moveTable(src, dst)
        self._qwidget._tablestack.moveWidget(src, dst)

    def _link_renamed_signals(self, i: int):
        """Link `name` property and tab text."""
        table = self._tablist[i]
        qtab = self._qwidget.addTable(table._qwidget, table.name)
        qtab.renamed.connect(partial(self._coerce_table_name_and_emit, table=table))
        qtab.buttonClicked.connect(partial(self._remove_table, table=table))
        table.events.renamed.connect(partial(self._coerce_table_name, table=table))
        table.events.renamed.connect(self.reset_choices)
        
    def _remove_backend_table(self, index: int, table: TableLayer):
        self._qwidget.removeTable(index)
    
    def _coerce_table_name_and_emit(self, name: str, table: TableLayer):
        self._coerce_table_name(name, table)
        table.events.renamed.emit(name)
    
    def _coerce_table_name(self, name: str, table: TableLayer):
        name = self._tablist._coerce_name(name, except_for=table)
        table._name = name
        self._qwidget.renameTable(table._qwidget, name)
    
    def _remove_table(self, table: TableLayer, _=None):
        self._tablist.remove(table)
        
    @property
    def tables(self) -> TableList:
        """Return the table list object."""
        return self._tablist
    
    @property
    def current_table(self) -> TableLayer:
        """Return the currently visible table."""
        return self.tables[self.current_index]
    
    @property
    def current_index(self) -> int:
        """Return the index of currently visible table."""
        return self._qwidget._tablist.currentIndex().row()
    
    @current_index.setter
    def current_index(self, value: int | str):
        if isinstance(value, str):
            value = self.tables.index(value)
        elif value < 0:
            value += len(self.tables)
        return self._qwidget._tablist.setCurrentRow(value)
    
    def register_action(self, location: str):
        return self._qwidget.registerAction(location)
    
    def show(self):
        """Show the widget."""
        self._qwidget.show()
    
    def add_table(self, data, *, name: str = None, editable: bool = False) -> TableLayer:
        table = TableLayer(data, name=name, editable=editable)
        return self.add_layer(table)
    
    def add_layer(self, layer):
        self.tables.append(layer)
        self.current_index = -1  # activate the last table
        return layer
    
    def add_dock_widget(
        self, 
        widget: Widget | QWidget,
        *,
        name: str = "",
        area: str = "right",
        allowed_areas: list[str] = None,
    ):
        if hasattr(widget, "native"):
            backend_widget = widget.native
            if not name:
                name = widget.name
        else:
            backend_widget = widget
            if not name:
                name = backend_widget.objectName()
            
        dock = self._qwidget.addDockWidget(
            backend_widget, name=name, area=area, allowed_areas=allowed_areas
        )
        dock.setSourceObject(widget)
        self._dock_widgets[name] = dock
        return dock
    
    def remove_dock_widget(self, name_or_widget):
        if isinstance(name_or_widget, str):
            name = name_or_widget
            dock = self._dock_widgets[name_or_widget]
        else:
            for k, v in self._dock_widgets.items():
                if v is name_or_widget:
                    name = k
                    dock = v
                    break
            else:
                raise ValueError(f"Widget {name_or_widget} not found.")
        self._qwidget.removeDockWidget(dock)
        self._dock_widgets.pop(name)
        return None
    
    def reset_choices(self, *_):
        for dock in self._dock_widgets.values():
            widget = dock.widget
            if hasattr(widget, "reset_choices"):
                widget.reset_choices()
    
    def read_csv(self, path, *args, **kwargs):
        import pandas as pd
        df = pd.read_csv(path, *args, **kwargs)
        name = Path(path).stem
        self.add_table(df, name=name)
        return df
    
    def read_excel(self, path, *args, **kwargs):
        import pandas as pd
        df_dict = pd.read_excel(path, *args, **kwargs)
        
        for sheet_name, df in df_dict.items():
            self.add_table(df, name=sheet_name)
        return df_dict

    def open(self, path: str | Path | bytes) -> None:
        path = Path(path)
        suf = path.suffix
        if suf in (".csv", ".txt", ".dat"):
            self.read_csv(path)
        elif suf in (".xlsx", ".xls", "xml"):
            self.read_excel(path)
        else:
            raise ValueError(f"Extension {suf} not supported.")