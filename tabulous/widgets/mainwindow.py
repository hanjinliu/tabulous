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
        self._tablist.events.moved.connect(self._move_backend_widget)
        self._qwidget._tablist.itemMoved.connect(self._move_table)
        
        if show:
            self.show()
    
    def _move_table(self, src: int, dst: int):
        with self._tablist.events.blocked():
            self._tablist.move(src, dst)
            self._qwidget._tablestack.moveWidget(src, dst)
        self._qwidget._tablestack.setCurrentIndex(dst)
    
    def _move_backend_widget(self, indices: tuple[int, int], item: TableLayer):
        src, dst = indices
        self._qwidget._tablist.moveTable(src, dst)
        self._qwidget._tablestack.moveWidget(src, dst)

    def _link_name(self, i: int):
        table = self._tablist[i]
        qtab = self._qwidget.addTable(table._qwidget, table.name)
        qtab.renamed.connect(partial(self._coerce_table_name_and_emit, table=table))
        qtab.buttonClicked.connect(partial(self._remove_table, table=table))
        table.events.renamed.connect(partial(self._coerce_table_name, table=table))
        
    def _disconnect_backend_table(self, index: int, table: TableLayer):
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
