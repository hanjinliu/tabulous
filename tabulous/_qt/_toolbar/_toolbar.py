from __future__ import annotations
from pathlib import Path
from typing import Callable, Hashable, TYPE_CHECKING, Union
from functools import partial
import weakref
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QAction

from .._svg import QColoredSVGIcon
from .._multitips import QHasToolTip
from . import _dialogs as _dlg


if TYPE_CHECKING:
    import pandas as pd
    from .._mainwindow import _QtMainWidgetBase
    from ...widgets.mainwindow import TableViewerBase
    from ...widgets import TableBase

SUMMARY_CHOICES = ["mean", "median", "std", "sem", "min", "max", "sum"]

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
        return None

    def toolTipPosition(self, index: int) -> QtCore.QPoint:
        btn, icon = self._button_and_icon[index]
        pos = btn.pos()
        pos.setY(pos.y() + btn.height() // 2)
        return pos

    def toolTipCount(self) -> int:
        return len(self._button_and_icon)

    def clickButton(self, index: int, *, ignore_index_error: bool = True):
        """Emulate a click on the button at the given index."""
        if index < 0 or index >= len(self._button_and_icon):
            if ignore_index_error:
                return None
            else:
                raise IndexError(f"Index {index} out of range")
        btn, icon = self._button_and_icon[index]
        return btn.click()


class QTableStackToolBar(QtW.QToolBar, QHasToolTip):
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
        self._child_widgets: weakref.WeakValueDictionary[
            str, QSubToolBar
        ] = weakref.WeakValueDictionary()

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
        toolbar.appendAction(f, qicon)
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
        return self.viewer._qwidget.openFromDialog(type="table")

    def open_spreadsheet(self):
        """Open a file as a spreadsheet."""
        return self.viewer._qwidget.openFromDialog(type="spreadsheet")

    def save_table(self):
        """Save current table."""
        return self.viewer._qwidget.saveFromDialog()

    def copy_as_table(self):
        """Make a copy of the current table."""
        viewer = self.viewer
        table = viewer.current_table
        if table is not None:
            viewer.add_table(table.data, name=f"{table.name}-copy")

    def copy_as_spreadsheet(self):
        """Make a copy of the current table."""
        viewer = self.viewer
        table = viewer.current_table
        if table is not None:
            viewer.add_spreadsheet(table.data, name=f"{table.name}-copy")

    def groupby(self):
        """Group table data by its column value."""
        table = self.viewer.current_table
        if table is not None:
            out = _dlg.groupby(
                df={"bind": table.data},
                by={"choices": list(table.data.columns), "widget_type": "Select"},
                parent=self,
            )
            if out is not None:
                self.viewer.add_groupby(out, name=f"{table.name}-groupby")

    def concat(self):
        """Concatenate tables."""
        out = _dlg.concat(
            viewer={"bind": self.viewer},
            names={
                "value": [self.viewer.current_table.name],
                "widget_type": "Select",
                "choices": [t.name for t in self.viewer.tables],
            },
            axis={"choices": [("vertical", 0), ("horizontal", 1)]},
            parent=self,
        )
        if out is not None:
            self.viewer.add_table(out, name=f"concat")

    def pivot(self):
        """Pivot a table."""
        table = self.viewer.current_table
        if table is None:
            return
        col = list(table.data.columns)
        if len(col) < 3:
            raise ValueError("Table must have at least three columns.")
        out = _dlg.pivot(
            df={"bind": table.data},
            index={"choices": col, "value": col[0]},
            columns={"choices": col, "value": col[1]},
            values={"choices": col, "value": col[2]},
        )
        if out is not None:
            self.viewer.add_table(out, name=f"{table.name}-pivot")

    def melt(self):
        """Unpivot a table."""
        table = self.viewer.current_table
        if table is None:
            return
        out = _dlg.melt(
            df={"bind": table.data},
            id_vars={"choices": list(table.data.columns), "widget_type": "Select"},
            parent=self,
        )
        if out is not None:
            self.viewer.add_table(out, name=f"{table.name}-melt")

    def summarize_table(self):
        """Summarize current table."""
        table = self.viewer.current_table
        if table is None:
            return
        out = _dlg.summarize_table(
            df={"bind": table.data},
            methods={"choices": SUMMARY_CHOICES, "widget_type": "Select"},
            parent=self,
        )
        if out is not None:
            df, new = out
            if new:
                self.viewer.add_table(df, name=f"{table.name}-summary")
            else:
                from .._table import QTableLayer

                qtable = QTableLayer(data=df)
                table.add_side_widget(qtable, name="summary")

    def toggle_console(self):
        """Toggle embedded console."""
        return self.parent().toggleConsoleVisibility()

    def find_item(self):
        """Toggle finder"""
        return self.parent()._tablestack.openFinderDialog()

    def sort_table(self):
        """Add sorted table."""
        table = self.viewer.current_table
        if table is None:
            return
        out = _dlg.sort(
            df={"bind": table.data},
            by={"choices": list(table.data.columns), "widget_type": "Select"},
            ascending={"text": "Sort in ascending order."},
            parent=self,
        )
        if out is not None:
            self.viewer.add_table(out, name=f"{table.name}-sorted")

    def selections_to_highlights(self):
        """Highlight selected regions."""
        table = self.viewer.current_table
        if table is None:
            return
        table.highlights = list(table.selections)
        return None

    def filter(self):
        """Apply filter to the current table."""
        return self.parent()._tablestack.openFilterDialog()

    def eval(self):
        """Evaluate a Python expression."""
        return self.parent()._tablestack.openEvalDialog()

    def change_view_mode(self, view_mode: str):
        """Change view mode."""
        table = self.viewer.current_table
        if table is None:
            return None
        table.view_mode = view_mode

    def plot(self):
        """Plot curve."""
        return self._plot_xy(_dlg.plot)

    def scatter(self):
        """Scatter plot."""
        return self._plot_xy(_dlg.scatter)

    def errorbar(self):
        """Errorbar plot."""
        table = self.viewer.current_table
        if table is None:
            return None

        data, choices = _get_data_and_choices(table)

        if len(choices) < 2:
            raise ValueError("Table must have at least two columns.")
        elif len(choices) == 2:
            x = {"choices": [], "value": None, "nullable": True}
            y = {"choices": choices, "value": choices[0]}
            yerr = {"choices": choices, "value": choices[1]}
        else:
            x = {"choices": choices, "nullable": True, "value": choices[0]}
            y = {"choices": choices, "value": choices[1]}
            yerr = {"choices": choices, "value": choices[2]}

        if _dlg.errorbar(
            ax={"bind": table.plt.gca()},
            x=x,
            y=y,
            yerr=yerr,
            data={"bind": data},
            alpha={"min": 0, "max": 1, "step": 0.05},
            parent=self,
        ):
            table.plt.draw()

    def hist(self):
        """Histogram."""
        table = self.viewer.current_table
        if table is None:
            return None

        data, choices = _get_data_and_choices(table)

        if _dlg.hist(
            ax={"bind": table.plt.gca()},
            y={"choices": choices, "widget_type": "Select", "value": choices[0]},
            data={"bind": data},
            alpha={"min": 0, "max": 1, "step": 0.05},
            histtype={
                "choices": ["bar", "step", "stepfilled", "barstacked"],
                "value": "bar",
            },
            parent=self,
        ):
            table.plt.draw()

    def swarmplot(self):
        """Swarm plot."""
        return self._plot_sns(_dlg.swarmplot)

    def barplot(self):
        """Bar plot."""
        return self._plot_sns(_dlg.barplot)

    def boxplot(self):
        """Box plot."""
        return self._plot_sns(_dlg.boxplot)

    def boxenplot(self):
        """Boxen plot."""
        return self._plot_sns(_dlg.boxenplot)

    def new_figure(self):
        """Add a new figure."""
        return self.viewer.current_table.plt.new_widget()

    def _plot_xy(self, dialog):
        table = self.viewer.current_table
        if table is None:
            return None

        data, choices = _get_data_and_choices(table)

        if len(choices) == 0:
            raise ValueError("Table must have at least one column.")
        elif len(choices) == 1:
            x = {"choices": [], "value": None, "nullable": True}
            y = {"choices": choices, "widget_type": "Select", "value": choices[0]}
        else:
            x = {"choices": choices, "nullable": True, "value": choices[0]}
            y = {"choices": choices, "widget_type": "Select", "value": choices[1]}

        if dialog(
            ax={"bind": table.plt.gca()},
            x=x,
            y=y,
            data={"bind": data},
            alpha={"min": 0, "max": 1, "step": 0.05},
            parent=self,
        ):
            table.plt.draw()

    def _plot_sns(self, dialog):
        table = self.viewer.current_table
        if table is None:
            return None

        colnames = list(table.data.columns)

        # infer x, y
        if len(colnames) == 0:
            raise ValueError("Table must have at least one column.")
        elif len(colnames) == 1:
            x = {"bind": None}
            y = {"bind": None}
        else:
            for i, dtype in enumerate(table.data.dtypes):
                if dtype == "categorical":
                    x = {"choices": colnames, "value": colnames[i], "nullable": True}
                    j = 0 if i > 0 else 1
                    y = {"choices": colnames, "value": colnames[j], "nullable": True}
                    break
            else:
                x = {"choices": colnames, "value": None, "nullable": True}
                y = {"choices": colnames, "value": None, "nullable": True}

        if dialog(
            ax={"bind": table.plt.gca()},
            x=x,
            y=y,
            data={"bind": table.data},
            hue={"choices": colnames, "nullable": True},
            parent=self,
        ):
            table.plt.draw()

    def initToolbar(self):
        """Add tool buttons"""

        # fmt: off
        # File
        self.registerAction("File", self.open_table, ICON_DIR / "open_table.svg")
        self.registerAction("File", self.open_spreadsheet, ICON_DIR / "open_spreadsheet.svg")
        self.registerAction("File", self.save_table, ICON_DIR / "save_table.svg")

        # Table
        self.registerAction("Table", self.copy_as_table, ICON_DIR / "copy_as_table.svg")
        self.registerAction("Table", self.copy_as_spreadsheet, ICON_DIR / "copy_as_spreadsheet.svg")
        self.addSeparatorToChild("Table")
        self.registerAction("Table", self.groupby, ICON_DIR / "groupby.svg")
        self.registerAction("Table", self.concat, ICON_DIR / "concat.svg")
        self.registerAction("Table", self.pivot, ICON_DIR / "pivot.svg")
        self.registerAction("Table", self.melt, ICON_DIR / "melt.svg")
        self.addSeparatorToChild("Table")
        self.registerAction("Table", self.find_item, ICON_DIR / "find_item.svg")
        self.registerAction("Table", self.sort_table, ICON_DIR / "sort_table.svg")
        self.registerAction("Table", self.selections_to_highlights, ICON_DIR / "selections_to_highlights.svg")

        # Analyze
        self.registerAction("Analyze", self.summarize_table, ICON_DIR / "summarize_table.svg")
        self.registerAction("Analyze", self.eval, ICON_DIR / "eval.svg")
        self.registerAction("Analyze", self.filter, ICON_DIR / "filter.svg")
        self.addSeparatorToChild("Analyze")
        self.registerAction("Analyze", self.toggle_console, ICON_DIR / "toggle_console.svg")

        # View
        self.registerAction("View", partial(self.change_view_mode, "popup"), ICON_DIR / "view_popup.svg")
        self.registerAction("View", partial(self.change_view_mode, "horizontal"), ICON_DIR / "view_dual_h.svg")
        self.registerAction("View", partial(self.change_view_mode, "vertical"), ICON_DIR / "view_dual_v.svg")
        self.registerAction("View", partial(self.change_view_mode, "normal"), ICON_DIR / "view_reset.svg")

        # Plot
        self.registerAction("Plot", self.plot, ICON_DIR / "plot.svg")
        self.registerAction("Plot", self.scatter, ICON_DIR / "scatter.svg")
        self.registerAction("Plot", self.errorbar, ICON_DIR / "errorbar.svg")
        self.registerAction("Plot", self.hist, ICON_DIR / "hist.svg")
        self.addSeparatorToChild("Plot")
        self.registerAction("Plot", self.swarmplot, ICON_DIR / "swarmplot.svg")
        self.registerAction("Plot", self.barplot, ICON_DIR / "barplot.svg")
        self.registerAction("Plot", self.boxplot, ICON_DIR / "boxplot.svg")
        self.registerAction("Plot", self.boxenplot, ICON_DIR / "boxenplot.svg")
        self.addSeparatorToChild("Plot")
        self.registerAction("Plot", self.new_figure, ICON_DIR / "new_figure.svg")

        # fmt: on


def _get_data_and_choices(
    table: TableBase,
) -> tuple[dict[Hashable, pd.Series], list[Hashable]]:
    data = dict(table.selections.values.itercolumns())
    choices = list(data.keys())

    if len(choices) == 0 or len(next(iter(data.values()))) == 1:
        # no selections or only one cell is selected
        data = dict(table.data.items())
        choices = list(table.data.columns)

    return data, choices
