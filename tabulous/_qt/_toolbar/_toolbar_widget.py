from __future__ import annotations
from pathlib import Path
from typing import Callable, TYPE_CHECKING, Union
from functools import partial
import weakref
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtWidgets import QAction

from tabulous._qt._svg import QColoredSVGIcon
from tabulous._qt._multitips import QHasToolTip
from tabulous import commands as cmds


if TYPE_CHECKING:
    from tabulous._qt._mainwindow import _QtMainWidgetBase
    from tabulous.widgets._mainwindow import TableViewerBase

ICON_DIR = Path(__file__).parent.parent / "_icons"


class QSubToolBar(QtW.QToolBar, QHasToolTip):
    """The child toolbar widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._button_and_icon: list[tuple[QtW.QToolButton, QColoredSVGIcon]] = []

    def updateIconColor(self, color):
        """Update all the icons with the given color."""
        for button, icon in self._button_and_icon:
            button.setIcon(icon.colored(color))

    def appendAction(self, f: Callable, qicon: QColoredSVGIcon):
        action = self.addAction(qicon, "")
        action.triggered.connect(f)
        if isinstance(f, partial):
            doc = f.func.__doc__
        else:
            doc = f.__doc__
        action.setToolTip(doc)
        btn = self.widgetForAction(action)
        self._button_and_icon.append((btn, qicon))
        return

    def toolTipPosition(self, index: int) -> QtCore.QPoint:
        btn, _ = self._button_and_icon[index]
        pos = btn.pos()
        pos.setY(pos.y() + btn.height() // 2)
        return pos

    def toolTipCount(self) -> int:
        return len(self._button_and_icon)

    def clickButton(self, index: int, *, ignore_index_error: bool = True):
        """Emulate a click on the button at the given index."""
        if index < 0 or index >= len(self._button_and_icon):
            if ignore_index_error:
                return
            else:
                raise IndexError("Index out of range")
        btn, _ = self._button_and_icon[index]
        return btn.click()


class QTableStackToolBar(QtW.QToolBar, QHasToolTip):
    _child_widgets: weakref.WeakValueDictionary[str, QSubToolBar]

    def __init__(self, parent: _QtMainWidgetBase):
        super().__init__(parent)

        self._tab = QtW.QTabWidget(self)
        self._tab.setContentsMargins(0, 0, 0, 0)
        self._tab.setStyleSheet(
            "QTabWidget {margin: 0px, 0px, 0px, 0px; padding: 0px;}"
        )
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Minimum
        )
        self._child_widgets = weakref.WeakValueDictionary()

        self.addWidget(self._tab)
        self.setMaximumHeight(120)
        self.initToolbar()

    @property
    def viewer(self) -> TableViewerBase:
        """The parent viewer object."""
        return self.parent()._table_viewer

    def currentIndex(self) -> int:
        """Current tab index."""
        return self._tab.currentIndex()

    def setCurrentIndex(self, index: int):
        """Set current tab index."""
        return self._tab.setCurrentIndex(index)

    def currentToolBar(self) -> QSubToolBar:
        """Current toolbar."""
        return self._child_widgets[self._tab.tabText(self._tab.currentIndex())]

    def toolTipPosition(self, index: int) -> QtCore.QPoint:
        return self._tab.tabBar().tabRect(index).topLeft()

    def toolTipText(self, index: int) -> str:
        return list(self._child_widgets.keys())[index][0]

    def toolTipCount(self) -> int:
        return self._tab.count()

    # fmt: off
    if TYPE_CHECKING:
        def parent(self) -> _QtMainWidgetBase: ...
    # fmt: on

    def addToolBar(self, name: str):
        """Add a tab of toolbar of name ``name``."""
        if name in self._child_widgets.keys():
            raise ValueError(f"Tab with name {name!r} already exists.")
        toolbar = QSubToolBar(self)
        toolbar.setContentsMargins(0, 0, 0, 0)
        self._tab.addTab(toolbar, name)
        self._child_widgets[name] = toolbar

    def registerAction(self, tabname: str, f: Callable, icon: Union[str, Path]):
        """Register a callback `f` in tab `tabname`."""
        if tabname not in self._child_widgets:
            self.addToolBar(tabname)
        toolbar = self._child_widgets[tabname]
        qicon = QColoredSVGIcon.fromfile(icon)
        fn = lambda: f(self.viewer)
        fn.__doc__ = f.__doc__
        toolbar.appendAction(fn, qicon)
        return

    def addSeparatorToChild(self, tabname: str) -> QAction:
        toolbar = self._child_widgets[tabname]
        return toolbar.addSeparator()

    def setToolButtonColor(self, color: str):
        """Update all the tool button colors."""
        for toolbar in self._child_widgets.values():
            toolbar.updateIconColor(color)

    # fmt: off
    def initToolbar(self):
        """Add tool buttons"""

        self.registerAction("Home", cmds.io.open_table, ICON_DIR / "open_table.svg")
        self.registerAction("Home", cmds.io.open_spreadsheet, ICON_DIR / "open_spreadsheet.svg")
        self.registerAction("Home", cmds.io.save_table, ICON_DIR / "save_table.svg")
        self.addSeparatorToChild("Home")
        self.registerAction("Home", cmds.io.open_sample, ICON_DIR / "open_sample.svg")
        self.addSeparatorToChild("Home")
        self.registerAction("Home", cmds.analysis.toggle_console, ICON_DIR / "toggle_console.svg")
        self.registerAction("Home", cmds.window.show_command_palette, ICON_DIR / "palette.svg")

        self.registerAction("Table", cmds.table.copy_as_table, ICON_DIR / "copy_as_table.svg")
        self.registerAction("Table", cmds.table.copy_as_spreadsheet, ICON_DIR / "copy_as_spreadsheet.svg")
        self.addSeparatorToChild("Table")
        self.registerAction("Table", cmds.table.groupby, ICON_DIR / "groupby.svg")
        self.registerAction("Table", cmds.table.switch_header, ICON_DIR / "switch_header.svg")
        self.registerAction("Table", cmds.table.concat, ICON_DIR / "concat.svg")
        self.registerAction("Table", cmds.table.pivot, ICON_DIR / "pivot.svg")
        self.registerAction("Table", cmds.table.melt, ICON_DIR / "melt.svg")
        self.addSeparatorToChild("Table")
        self.registerAction("Table", cmds.table.show_finder_widget, ICON_DIR / "find_item.svg")
        self.registerAction("Table", cmds.table.sort_table, ICON_DIR / "sort_table.svg")
        self.addSeparatorToChild("Table")
        self.registerAction("Table", cmds.table.random, ICON_DIR / "random.svg")

        self.registerAction("Analyze", cmds.analysis.summarize_table, ICON_DIR / "summarize_table.svg")
        self.registerAction("Analyze", cmds.analysis.show_eval_widget, ICON_DIR / "eval.svg")
        self.registerAction("Analyze", cmds.analysis.show_filter_widget, ICON_DIR / "filter.svg")
        self.addSeparatorToChild("Analyze")
        self.registerAction("Analyze", cmds.analysis.show_optimizer_widget, ICON_DIR / "optimize.svg")
        self.registerAction("Analyze", cmds.analysis.show_stats_widget, ICON_DIR / "stats_test.svg")
        self.registerAction("Analyze", cmds.analysis.show_sklearn_widget, ICON_DIR / "sklearn_analysis.svg")

        self.registerAction("View", cmds.view.set_popup_mode, ICON_DIR / "view_popup.svg")
        self.registerAction("View", cmds.view.set_dual_h_mode, ICON_DIR / "view_dual_h.svg")
        self.registerAction("View", cmds.view.set_dual_v_mode, ICON_DIR / "view_dual_v.svg")
        self.registerAction("View", cmds.view.reset_view_mode, ICON_DIR / "view_reset.svg")
        self.addSeparatorToChild("View")
        self.registerAction("View", cmds.view.tile_tables, ICON_DIR / "tile.svg")
        self.registerAction("View", cmds.view.untile_table, ICON_DIR / "untile.svg")

        self.registerAction("Plot", cmds.plot.plot, ICON_DIR / "plot.svg")
        self.registerAction("Plot", cmds.plot.scatter, ICON_DIR / "scatter.svg")
        self.registerAction("Plot", cmds.plot.errorbar, ICON_DIR / "errorbar.svg")
        self.registerAction("Plot", cmds.plot.hist, ICON_DIR / "hist.svg")
        self.addSeparatorToChild("Plot")
        self.registerAction("Plot", cmds.plot.swarmplot, ICON_DIR / "swarmplot.svg")
        self.registerAction("Plot", cmds.plot.barplot, ICON_DIR / "barplot.svg")
        self.registerAction("Plot", cmds.plot.boxplot, ICON_DIR / "boxplot.svg")
        self.registerAction("Plot", cmds.plot.boxenplot, ICON_DIR / "boxenplot.svg")
        self.addSeparatorToChild("Plot")
        self.registerAction("Plot", cmds.plot.new_figure, ICON_DIR / "new_figure.svg")

        return
    # fmt: on
