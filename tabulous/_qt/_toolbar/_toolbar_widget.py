from __future__ import annotations
from pathlib import Path
from typing import Callable, TYPE_CHECKING, Union
from functools import partial
import weakref
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QAction

from tabulous._qt._svg import QColoredSVGIcon
from tabulous._qt._multitips import QHasToolTip
from tabulous import commands as cmds

from ._toolbutton import QColoredToolButton, QMoreToolButton
from ._corner import QSelectionRangeEdit

if TYPE_CHECKING:
    from tabulous._qt._mainwindow import _QtMainWidgetBase
    from tabulous.widgets._mainwindow import TableViewerBase

ICON_DIR = Path(__file__).parent.parent / "_icons"


class QSubToolBar(QtW.QToolBar, QHasToolTip):
    """The child toolbar widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons: list[QColoredToolButton] = []

    def updateIconColor(self, color):
        """Update all the icons with the given color."""
        for button in self._buttons:
            button.updateColor(color)

    def appendAction(self, f: Callable, qicon: QColoredSVGIcon):
        """Add function ``f`` to the toolbar with the given icon."""
        btn = QColoredToolButton()
        self.addWidget(btn)
        btn.setIcon(qicon)
        btn.clicked.connect(f)
        if isinstance(f, partial):
            doc = f.func.__doc__
        else:
            doc = f.__doc__
        btn.setToolTip(doc)
        self._buttons.append(btn)
        return

    def appendMenuAction(self, f: Callable, name: str):
        btn = self._buttons[-1]
        if not isinstance(btn, QMoreToolButton):
            btn = QMoreToolButton()

            self.addWidget(btn)
            self._buttons.append(btn)

        menu = btn.menu()
        if menu is None:
            menu = QtW.QMenu(self)
            btn.setMenu(menu)

        action = menu.addAction(name)
        action.triggered.connect(f)
        if isinstance(f, partial):
            doc = f.func.__doc__
        else:
            doc = f.__doc__
        action.setToolTip(doc)
        return

    def toolTipPosition(self, index: int) -> QtCore.QPoint:
        btn = self._buttons[index]
        pos = btn.pos()
        pos.setY(pos.y() + btn.height() // 2)
        return pos

    def toolTipCount(self) -> int:
        return len(self._buttons)

    def clickButton(self, index: int, *, ignore_index_error: bool = True):
        """Emulate a click on the button at the given index."""
        if index < 0 or index >= len(self._buttons):
            if ignore_index_error:
                return
            else:
                raise IndexError("Index out of range")
        btn = self._buttons[index]
        return btn.click()


class QTableStackToolBar(QtW.QToolBar, QHasToolTip):
    _child_widgets: weakref.WeakValueDictionary[str, QSubToolBar]
    sliceChanged = Signal(object)

    def __init__(self, parent: _QtMainWidgetBase):
        super().__init__(parent)

        self._tab = QtW.QTabWidget(self)
        self._tab.setContentsMargins(0, 0, 0, 0)
        corner = QSelectionRangeEdit(self._tab)
        self._corner_widget = corner
        self._tab.setCornerWidget(corner)
        corner.sliceChanged.connect(self.sliceChanged.emit)
        corner.hide()

        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Minimum
        )
        self._child_widgets = weakref.WeakValueDictionary()

        self.addWidget(self._tab)
        self.setMaximumHeight(84)
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

        def fn():
            return f(self.viewer)

        fn.__doc__ = f.__doc__
        toolbar.appendAction(fn, qicon)
        return

    def addSeparatorToChild(self, tabname: str) -> QAction:
        toolbar = self._child_widgets[tabname]
        return toolbar.addSeparator()

    def registerMenuAction(self, tabname: str, f: Callable, name: str | None = None):
        """Register a menu in tab `tabname`."""
        toolbar = self._child_widgets[tabname]
        if name is None:
            name = f.__name__.replace("_", " ").capitalize()

        def fn():
            return f(self.viewer)

        fn.__doc__ = f.__doc__
        toolbar.appendMenuAction(fn, name)
        return None

    def setToolButtonColor(self, color: str):
        """Update all the tool button colors."""
        for toolbar in self._child_widgets.values():
            toolbar.updateIconColor(color)

    # fmt: off
    def initToolbar(self):
        """Add tool buttons"""

        main = self.parent()._is_mainwindow

        self.registerAction("Home", cmds.file.open_table, ICON_DIR / "open_table.svg")  # noqa: E501
        self.registerAction("Home", cmds.file.open_spreadsheet, ICON_DIR / "open_spreadsheet.svg")  # noqa: E501
        self.registerAction("Home", cmds.file.save_table, ICON_DIR / "save_table.svg")  # noqa: E501
        self.addSeparatorToChild("Home")
        self.registerAction("Home", cmds.file.open_sample, ICON_DIR / "open_sample.svg")  # noqa: E501
        self.addSeparatorToChild("Home")
        self.registerAction("Home", cmds.window.toggle_console, ICON_DIR / "toggle_console.svg")  # noqa: E501
        self.registerAction("Home", cmds.window.show_command_palette, ICON_DIR / "palette.svg")  # noqa: E501
        if main:
            self.addSeparatorToChild("Home")
            self.registerAction("Home", cmds.window.show_preference, ICON_DIR / "preferences.svg")  # noqa: E501

        self.registerAction("Edit", cmds.selection.copy_data_tab_separated, ICON_DIR / "copy.svg")  # noqa: E501
        self.registerAction("Edit", cmds.selection.paste_data_tab_separated, ICON_DIR / "paste.svg")  # noqa: E501
        self.registerAction("Edit", cmds.selection.cut_data, ICON_DIR / "cut.svg")  # noqa: E501
        self.addSeparatorToChild("Edit")
        self.registerAction("Edit", cmds.table.undo_table, ICON_DIR / "undo.svg")  # noqa: E501
        self.registerAction("Edit", cmds.table.redo_table, ICON_DIR / "redo.svg")  # noqa: E501

        self.registerAction("Table", cmds.table.copy_as_table, ICON_DIR / "copy_as_table.svg")  # noqa: E501
        self.registerAction("Table", cmds.table.copy_as_spreadsheet, ICON_DIR / "copy_as_spreadsheet.svg")  # noqa: E501
        self.addSeparatorToChild("Table")
        self.registerAction("Table", cmds.column.run_groupby, ICON_DIR / "groupby.svg")  # noqa: E501
        self.registerAction("Table", cmds.table.switch_columns, ICON_DIR / "switch_header.svg")  # noqa: E501
        self.registerAction("Table", cmds.table.pivot, ICON_DIR / "pivot.svg")
        self.registerAction("Table", cmds.table.melt, ICON_DIR / "melt.svg")
        self.addSeparatorToChild("Table")
        self.registerAction("Table", cmds.table.random, ICON_DIR / "random.svg")  # noqa: E501
        self.registerAction("Table", cmds.table.round, ICON_DIR / "round.svg")  # noqa: E501

        self.registerAction("Analyze", cmds.analysis.summarize_table, ICON_DIR / "summarize_table.svg")  # noqa: E501
        self.registerAction("Analyze", cmds.analysis.show_eval_widget, ICON_DIR / "eval.svg")  # noqa: E501
        self.registerAction("Analyze", cmds.table.show_finder_widget, ICON_DIR / "find_item.svg")  # noqa: E501
        self.registerAction("Analyze", cmds.selection.sort_by_columns, ICON_DIR / "sort_table.svg")  # noqa: E501
        self.registerAction("Analyze", cmds.analysis.show_filter_widget, ICON_DIR / "filter.svg")  # noqa: E501
        self.addSeparatorToChild("Analyze")
        self.registerAction("Analyze", cmds.analysis.show_optimizer_widget, ICON_DIR / "optimize.svg")  # noqa: E501
        self.registerAction("Analyze", cmds.analysis.show_stats_widget, ICON_DIR / "stats_test.svg")  # noqa: E501
        self.registerAction("Analyze", cmds.analysis.show_sklearn_widget, ICON_DIR / "sklearn_analysis.svg")  # noqa: E501

        self.registerAction("View", cmds.view.set_popup_mode, ICON_DIR / "view_popup.svg")  # noqa: E501
        self.registerAction("View", cmds.view.set_dual_h_mode, ICON_DIR / "view_dual_h.svg")  # noqa: E501
        self.registerAction("View", cmds.view.set_dual_v_mode, ICON_DIR / "view_dual_v.svg")  # noqa: E501
        self.registerAction("View", cmds.view.reset_view_mode, ICON_DIR / "view_reset.svg")  # noqa: E501
        self.addSeparatorToChild("View")
        self.registerAction("View", cmds.tab.tile_tables, ICON_DIR / "tile.svg")  # noqa: E501
        self.registerAction("View", cmds.tab.untile_table, ICON_DIR / "untile.svg")  # noqa: E501
        self.addSeparatorToChild("View")
        self.registerAction("View", cmds.table.switch_layout, ICON_DIR / "switch_layout.svg")  # noqa: E501

        self.registerAction("Plot", cmds.plot.plot, ICON_DIR / "plot.svg")
        self.registerAction("Plot", cmds.plot.scatter, ICON_DIR / "scatter.svg")  # noqa: E501
        self.registerAction("Plot", cmds.plot.hist, ICON_DIR / "hist.svg")
        self.registerMenuAction("Plot", cmds.plot.bar, name="Run plt.bar")
        self.registerMenuAction("Plot", cmds.plot.errorbar, name="Run plt.errorbar")  # noqa: E501
        self.registerMenuAction("Plot", cmds.plot.fill_between, name="Run plt.fill_between")  # noqa: E501
        self.registerMenuAction("Plot", cmds.plot.fill_betweenx, name="Run plt.fill_betweenx")  # noqa: E501
        self.addSeparatorToChild("Plot")
        self.registerAction("Plot", cmds.plot.swarmplot, ICON_DIR / "swarmplot.svg")  # noqa: E501
        self.registerAction("Plot", cmds.plot.barplot, ICON_DIR / "barplot.svg")  # noqa: E501
        self.registerAction("Plot", cmds.plot.boxplot, ICON_DIR / "boxplot.svg")  # noqa: E501
        self.registerMenuAction("Plot", cmds.plot.boxenplot, name="Run sns.boxenplot")  # noqa: E501
        self.registerMenuAction("Plot", cmds.plot.stripplot, name="Run sns.stripplot")  # noqa: E501
        self.registerMenuAction("Plot", cmds.plot.violinplot, name="Run sns.violinplot")  # noqa: E501
        self.addSeparatorToChild("Plot")
        self.registerAction("Plot", cmds.plot.new_figure, ICON_DIR / "new_figure.svg")  # noqa: E501

        return
    # fmt: on
