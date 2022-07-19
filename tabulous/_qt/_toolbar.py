# from __future__ import annotations
from pathlib import Path
from typing import Callable, List, TYPE_CHECKING, Union
import weakref
import numpy as np
import pandas as pd
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtWidgets import QAction

from ._svg import QColoredSVGIcon
from .._magicgui import dialog_factory
from ..types import TableData

if TYPE_CHECKING:
    from ._mainwindow import _QtMainWidgetBase
    from ..widgets.mainwindow import _TableViewerBase

SUMMARY_CHOICES = ["mean", "median", "std", "sem", "min", "max", "sum"]

ICON_DIR = Path(__file__).parent / "_icons"


class _QToolBar(QtW.QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._button_and_icon: List["tuple[QtW.QToolButton, QColoredSVGIcon]"] = []

    def updateIconColor(self, color):
        for button, icon in self._button_and_icon:
            button.setIcon(icon.colored(color))


class QTableStackToolBar(QtW.QToolBar):
    def __init__(self, parent: "_QtMainWidgetBase"):
        super().__init__(parent)

        self._tab = QtW.QTabWidget(self)
        self._tab.setContentsMargins(0, 0, 0, 0)
        self._tab.setStyleSheet(
            r"QTabWidget {margin: 0px, 0px, 0px, 0px; padding: 0px;}"
        )
        self._child_widgets: weakref.WeakValueDictionary[
            str, _QToolBar
        ] = weakref.WeakValueDictionary()

        self.addWidget(self._tab)
        self.registerAction("File", self.open_table, ICON_DIR / "open_table.svg")
        self.registerAction(
            "File", self.open_spreadsheet, ICON_DIR / "open_spreadsheet.svg"
        )
        self.registerAction("File", self.save_table, ICON_DIR / "save_table.svg")

        self.registerAction("Table", self.copy_as_table, ICON_DIR / "copy_as_table.svg")
        self.registerAction(
            "Table", self.copy_as_spreadsheet, ICON_DIR / "copy_as_spreadsheet.svg"
        )
        self.registerAction(
            "Table", self.new_spreadsheet, ICON_DIR / "new_spreadsheet.svg"
        )
        self.addSeparatorToChild("Table")
        self.registerAction("Table", self.groupby, ICON_DIR / "groupby.svg")
        self.registerAction("Table", self.hconcat, ICON_DIR / "hconcat.svg")
        self.registerAction("Table", self.vconcat, ICON_DIR / "vconcat.svg")
        self.registerAction("Table", self.pivot, ICON_DIR / "pivot.svg")
        self.registerAction("Table", self.melt, ICON_DIR / "melt.svg")
        self.addSeparatorToChild("Table")
        self.registerAction("Table", self.query, ICON_DIR / "query.svg")

        self.registerAction(
            "Analyze", self.summarize_table, ICON_DIR / "summarize_table.svg"
        )
        self.addSeparatorToChild("Analyze")

    @property
    def viewer(self) -> "_TableViewerBase":
        """The parent viewer object."""
        return self.parent()._table_viewer

    if TYPE_CHECKING:

        def parent(self) -> "_QtMainWidgetBase":
            ...

    def addToolBar(self, name: str):
        """Add a tab of toolbar of name ``name``."""
        if name in self._child_widgets.keys():
            raise ValueError(f"Tab with name {name!r} already exists.")
        toolbar = _QToolBar(self)
        toolbar.setContentsMargins(0, 0, 0, 0)
        self._tab.addTab(toolbar, name)
        self._child_widgets[name] = toolbar

    def registerAction(self, tabname: str, f: Callable, icon: Union[str, Path]):
        """Register a callback `f` in tab `tabname`."""
        if tabname not in self._child_widgets:
            self.addToolBar(tabname)
        toolbar = self._child_widgets[tabname]
        qicon = QColoredSVGIcon.fromfile(str(icon))
        action = toolbar.addAction(qicon, "")
        action.triggered.connect(f)
        action.setToolTip(f.__doc__)
        toolbar._button_and_icon.append((toolbar.widgetForAction(action), qicon))
        return None

    def addSeparatorToChild(self, tabname: str) -> QAction:
        toolbar = self._child_widgets[tabname]
        return toolbar.addSeparator()

    def setToolButtonColor(self, color: str):
        """Update all the tool button colors."""
        for toolbar in self._child_widgets.values():
            toolbar.updateIconColor(color)

    def open_table(self):
        """Open a file as a table."""
        return self._open(type="table")

    def open_spreadsheet(self):
        """Open a file as a spreadsheet."""
        return self._open(type="spreadsheet")

    def _open(self, type):
        # TODO: history
        paths, _ = QtW.QFileDialog.getOpenFileNames(self.parent(), "Open File", "")
        for path in paths:
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

    def groupby(self):
        """Group table data by its column value."""
        table = self.viewer.current_table
        out = groupby(
            df={"bind": table.data},
            by={"choices": list(table.data.columns), "widget_type": "Select"},
        )
        if out is not None:
            self.viewer.add_groupby(out, name=f"{table.name}-groupby")

    def hconcat(self):
        """Concatenate tables horizontally."""
        out = hconcat(
            viewer={"bind": self.viewer},
            names={
                "value": [self.viewer.current_table.name],
                "widget_type": "Select",
                "choices": [t.name for t in self.viewer.tables],
            },
        )
        if out is not None:
            self.viewer.add_table(out, name=f"hconcat")

    def vconcat(self):
        """Concatenate tables vertically."""
        out = vconcat(
            viewer={"bind": self.viewer},
            names={
                "value": [self.viewer.current_table.name],
                "widget_type": "Select",
                "choices": [t.name for t in self.viewer.tables],
            },
        )
        if out is not None:
            self.viewer.add_table(out, name=f"vconcat")

    def pivot(self):
        """Pivot a table."""
        table = self.viewer.current_table
        col = list(table.data.columns)
        if len(col) < 2:
            raise ValueError("Table must have at least two columns.")
        out = pivot(
            df={"bind": table.data},
            index={"choices": col, "value": col[0]},
            columns={"choices": col, "value": col[1]},
            values={"choices": col, "nullable": True},
        )
        if out is not None:
            self.viewer.add_table(out, name=f"{table.name}-pivot")

    def melt(self):
        """Unpivot a table."""
        table = self.viewer.current_table
        out = melt(
            df={"bind": table.data},
            id_vars={"choices": list(table.data.columns), "widget_type": "Select"},
        )
        if out is not None:
            self.viewer.add_table(out, name=f"{table.name}-melt")

    def summarize_table(self):
        """Summarize current table."""
        table = self.viewer.current_table
        out = summarize_table(
            df={"bind": table.data},
            methods={"choices": SUMMARY_CHOICES, "widget_type": "Select"},
        )
        if out is not None:
            self.viewer.add_table(out, name=f"{table.name}-summary")

    def query(self):
        """Filter table using a query."""
        table = self.viewer.current_table
        out = query(df={"bind": table.data})
        if out is not None:
            self.viewer.add_table(out, name=f"{table.name}-query")


@dialog_factory
def summarize_table(df: TableData, methods: List[str]):
    return df.agg(methods)


@dialog_factory
def groupby(df: TableData, by: List[str]):
    return df.groupby(by)


@dialog_factory
def hconcat(viewer, names: List[str]):
    dfs = [viewer.tables[name].data for name in names]
    return pd.concat(dfs, axis=0)


@dialog_factory
def vconcat(viewer, names: List[str]):
    dfs = [viewer.tables[name].data for name in names]
    return pd.concat(dfs, axis=1)


@dialog_factory
def pivot(df: TableData, index: str, columns: str, values: str):
    return df.pivot(index=index, columns=columns, values=values)


@dialog_factory
def melt(df: TableData, id_vars: List[str]):
    return pd.melt(df, id_vars)


@dialog_factory
def query(df: TableData, expr: str):
    return df.query(expr)
