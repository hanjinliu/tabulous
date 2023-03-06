from __future__ import annotations
from typing import TYPE_CHECKING
from . import _dialogs, _utils
from tabulous._magicgui import ToggleSwitchSelect

if TYPE_CHECKING:
    from tabulous.widgets._mainwindow import TableViewerBase
    import pandas as pd

SUMMARY_CHOICES = [
    "mean",
    "median",
    "std",
    "sem",
    "min",
    "max",
    "sum",
    "nunique",
    "dtype",
]


def summarize_table(viewer: TableViewerBase):
    """Summarize table data"""
    table = _utils.get_table(viewer)
    out = _dialogs.summarize_table(
        table={"bind": table},
        methods={"choices": SUMMARY_CHOICES, "widget_type": ToggleSwitchSelect},
        parent=viewer._qwidget,
    )
    if out is not None:
        df, new = out
        if new:
            viewer.add_table(df, name=f"{table.name}-summary")
        else:
            from tabulous._qt._table import QTableLayer

            qtable = QTableLayer(data=df)
            qtable.setZoom(0.8)
            table.add_side_widget(qtable, name="summary")


def polynomial_fit(viewer: TableViewerBase):
    """Polynomial fitting of 1D data"""
    from ._regression import PolynomialFitWidget
    from tabulous.widgets import Table

    table = _utils.get_table(viewer)
    wdt = PolynomialFitWidget()

    @wdt.called.connect
    def _on_called(df: pd.DataFrame):
        table.add_side_widget(Table(df, editable=False), name="Polynomial fit")

    wdt.native.setParent(viewer.native, wdt.native.windowFlags())
    wdt.show()


def show_filter_widget(viewer: TableViewerBase):
    """Show filter widget."""
    return viewer._qwidget._tablestack.openFilterDialog()


def show_eval_widget(viewer: TableViewerBase):
    """Evaluate a Python expression"""
    return viewer._qwidget._tablestack.openEvalDialog()


def show_optimizer_widget(viewer: TableViewerBase):
    """Open optimizer widget"""
    from ._optimizer import OptimizerWidget

    tablestack = viewer._qwidget._tablestack
    ol = tablestack._overlay
    ol.show()

    ol.addWidget(OptimizerWidget.new().native)
    ol.setTitle("Optimization")


def show_stats_widget(viewer: TableViewerBase):
    """Open scipy.stats widget"""
    from ._statistics import StatsTestDialog

    dlg = StatsTestDialog()
    dlg.native.setParent(viewer._qwidget, dlg.native.windowFlags())
    dlg.show()


def show_sklearn_widget(viewer: TableViewerBase):
    """Open scikit-learn widget"""
    from ._sklearn import SkLearnContainer

    tablestack = viewer._qwidget._tablestack
    ol = tablestack._overlay
    ol.show()

    ol.addWidget(SkLearnContainer.new().native)
    ol.setTitle("scikit-learn analysis")
