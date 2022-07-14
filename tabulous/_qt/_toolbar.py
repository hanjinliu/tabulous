from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Callable
import weakref
import numpy as np
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtWidgets import QAction

from .._magicgui import dialog_factory

if TYPE_CHECKING:
    import pandas as pd
    from ._mainwindow import _QtMainWidgetBase
    from ..widgets.mainwindow import _TableViewerBase

SUMMARY_CHOICES = ["mean", "median", "std", "sem", "min", "max", "sum"]

ICON_DIR = Path(__file__).parent / "_icons"

class QTableStackToolBar(QtW.QToolBar):
    def __init__(self, parent: _QtMainWidgetBase):
        super().__init__(parent)
        
        self._tab = QtW.QTabWidget(self)
        self._tab.setContentsMargins(0, 0, 0, 0)
        self._tab.setStyleSheet(
            r"QTabWidget {margin: 0px, 0px, 0px, 0px; padding: 0px;}"
        )
        self._child_widgets: weakref.WeakValueDictionary[str, QtW.QToolBar] = weakref.WeakValueDictionary()
        
        self.addWidget(self._tab)
        sp = QtW.QStyle.StandardPixmap
        self.registerAction("File", self.open_table, ICON_DIR / "open_table.svg")
        self.registerAction("File", self.open_spreadsheet, ICON_DIR / "open_spreadsheet.svg")
        self.registerAction("File", self.save_table, sp.SP_DialogSaveButton)
        self.registerAction("Table", self.copy_as_table, ICON_DIR / "copy_as_table.svg")
        self.registerAction("Table", self.copy_as_spreadsheet, ICON_DIR / "copy_as_spreadsheet.svg")
        self.registerAction("Table", self.new_spreadsheet, ICON_DIR / "new_spreadsheet.svg")
        self.registerAction("Analyze", self.summarize_table, ICON_DIR / "summarize_table.svg")
    
    @property
    def viewer(self) -> _TableViewerBase:
        return self.parent()._table_viewer

    if TYPE_CHECKING:
        def parent(self) -> _QtMainWidgetBase:
            ...
    
    def addToolBar(self, name: str):
        if name in self._child_widgets.keys():
            raise ValueError(f"Tab with name {name!r} already exists.")
        toolbar = QtW.QToolBar(self)
        toolbar.setContentsMargins(0, 0, 0, 0)
        self._tab.addTab(toolbar, name)
        self._child_widgets[name] = toolbar
        
    def registerAction(self, tabname: str, f: Callable, icon: str | Path | int):
        if tabname not in self._child_widgets:
            self.addToolBar(tabname)
        toolbar = self._child_widgets[tabname]
        if isinstance(icon, int):
            qicon = QtW.QApplication.style().standardIcon(icon)
        else:
            qicon = QtGui.QIcon(str(icon))
        action = QAction(qicon, "", self)
        action.triggered.connect(f)
        action.setToolTip(f.__doc__)
        toolbar.addAction(action)
        return None
    
    def open_table(self):
        """Open a file as a table."""
        return self._open(type="table")
        
    def open_spreadsheet(self):
        """Open a file as a spreadsheet."""
        return self._open(type="spreadsheet")
    
    def _open(self, type):
        # TODO: history
        path, _ = QtW.QFileDialog.getOpenFileName(self.parent(), "Open File", "")
        if path:
            self.viewer.open(path, type=type)
        return None
        
    def save_table(self):
        """Save current table."""
        path, _ = QtW.QFileDialog.getSaveFileName(self.parent(), "Save Table", "")
        if path:
            self.viewer.save(path)
    
    def copy_as_table(self):
        """Make a copy of the current table."""
        viewer = self.viewer
        table = viewer.current_table
        viewer.add_table(table.data, name=f"{table.name}-copy")
    
    def copy_as_spreadsheet(self):
        """Make a copy of the current table."""
        viewer = self.viewer
        table = viewer.current_table
        viewer.add_spreadsheet(table.data, name=f"{table.name}-copy")
    
    def new_spreadsheet(self):
        """Create a new spreadsheet."""
        self.viewer.add_spreadsheet(name="New")

    def summarize_table(self):
        """Summarize current table."""
        table = self.viewer.current_table
        out = summarize_table(
            df={"bind": table.data}, 
            methods={"choices": SUMMARY_CHOICES, "widget_type": "Select"}
        )
        if out is not None:
            self.viewer.add_table(out, name=f"{table.name}-summary")
        
@dialog_factory
def summarize_table(df, methods: list[str]):
    return df.agg(methods)
