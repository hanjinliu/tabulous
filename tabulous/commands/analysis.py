from __future__ import annotations
from typing import TYPE_CHECKING
from . import _dialogs, _utils

if TYPE_CHECKING:
    from tabulous.widgets._mainwindow import TableViewerBase

SUMMARY_CHOICES = ["mean", "median", "std", "sem", "min", "max", "sum"]


def summarize_table(viewer: TableViewerBase):
    """Summarize current table."""
    table = _utils.get_table(viewer)
    out = _dialogs.summarize_table(
        df={"bind": table.data},
        methods={"choices": SUMMARY_CHOICES, "widget_type": "Select"},
        parent=viewer._qwidget,
    )
    if out is not None:
        df, new = out
        if new:
            viewer.add_table(df, name=f"{table.name}-summary")
        else:
            from tabulous._qt._table import QTableLayer

            qtable = QTableLayer(data=df)
            table.add_side_widget(qtable, name="summary")


def toggle_console(viewer: TableViewerBase):
    """Toggle embedded console."""
    return viewer._qwidget.toggleConsoleVisibility()


def show_filter_widget(viewer: TableViewerBase):
    """Apply filter to the current table."""
    return viewer._qwidget._tablestack.openFilterDialog()


def show_eval_widget(viewer: TableViewerBase):
    """Evaluate a Python expression."""
    return viewer._qwidget._tablestack.openEvalDialog()


def optimize(viewer: TableViewerBase):
    """Open the optimizer widget."""
    from ._optimizer import OptimizerWidget

    tablestack = viewer._qwidget._tablestack
    ol = tablestack._overlay
    ol.show()

    ol.addWidget(OptimizerWidget.new().native)
    ol.setTitle("Optimization")


def stats_test(viewer: TableViewerBase):
    from ._statistics import StatsTestDialog

    dlg = StatsTestDialog()
    dlg.native.setParent(viewer._qwidget, dlg.native.windowFlags())
    dlg.show()


def sklearn_analysis(viewer: TableViewerBase):
    from ._sklearn import SkLearnContainer

    tablestack = viewer._qwidget._tablestack
    ol = tablestack._overlay
    ol.show()

    ol.addWidget(SkLearnContainer.new().native)
    ol.setTitle("scikit-learn analysis")
