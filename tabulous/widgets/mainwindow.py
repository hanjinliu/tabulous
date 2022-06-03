from __future__ import annotations
from functools import partial
from pathlib import Path
import pandas as pd

from .._qt import QMainWindow, get_app

from .table import TableLayer
from .tablelist import TableList

class TableViewer:
    
    def __init__(self, *, show: bool = True):
        app = get_app()
        self._qwidget = QMainWindow()
        self._qwidget._table_viewer = self
        self._tablist = TableList(parent=self)
        self._tablist.events.inserted.connect(self._link_name)
        self._tablist.events.removed.connect(self._disconnect_backend_table)
        if show:
            self.show()
    
    def _link_name(self, i: int):
        table = self._tablist[i]
        qtab = self._qwidget.addTable(table._qwidget, table.name)
        qtab.renamed.connect(partial(self._coerce_and_rename, table=table))
        table.events.renamed.connect(partial(self._coerce_and_set_text, table=table))
        
    def _disconnect_backend_table(self, index: int, table: TableLayer):
        self._qwidget.removeTable(index)
        del table._qwidget, table
    
    def _coerce_and_rename(self, name: str, table: TableLayer):
        name = self._tablist._coerce_name(name, except_for=table)
        table._set_name(name)
        table.events.renamed.emit(name)
        self._qwidget.renameTable(table._qwidget, name)
    
    def _coerce_and_set_text(self, name: str, table: TableLayer):
        name = self._tablist._coerce_name(name, except_for=table)
        table._name = name
        self._qwidget.renameTable(table._qwidget, name)
        
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
        return self._qwidget.stackIndex()
    
    @current_index.setter
    def current_index(self, value: int | str):
        if isinstance(value, str):
            value = self.tables.index(value)
        elif value < 0:
            value += len(self.tables)
        return self._qwidget.setStackIndex(value)
    
    def show(self):
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
        widget,
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
            
        self._qwidget.addDockWidget(
            backend_widget, name=name, area=area, allowed_areas=allowed_areas
        )

    
    def read_csv(self, path, *args, **kwargs):
        df = pd.read_csv(path, *args, **kwargs)
        name = Path(path).stem
        self.add_table(df, name=name)
        return df
    
    def read_excel(self, path, *args, **kwargs):
        df_dict = pd.read_excel(path, *args, **kwargs)
        
        for sheet_name, df in df_dict.items():
            self.add_table(df, name=sheet_name)
        return df_dict
