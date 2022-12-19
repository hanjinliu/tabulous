from __future__ import annotations

from typing import Hashable, TYPE_CHECKING, NamedTuple
from . import _dialogs


if TYPE_CHECKING:
    from tabulous.widgets import TableBase, TableViewerBase


def plot(viewer: TableViewerBase):
    """Run plt.plot"""
    return _plot_xy(viewer, _dialogs.plot)


def bar(viewer: TableViewerBase):
    """Run plt.bar"""
    return _plot_xy(viewer, _dialogs.bar)


def scatter(viewer: TableViewerBase):
    """Run plt.scatter"""
    return _plot_xy(viewer, _dialogs.scatter)


def errorbar(viewer: TableViewerBase):
    """Run plt.errorbar"""
    table = viewer.current_table
    if table is None:
        return

    _dialogs.errorbar(
        ax={"bind": table.plt.gca()},
        table={"bind": table},
        alpha={"min": 0, "max": 1, "step": 0.05},
        parent=viewer._qwidget,
    )


def hist(viewer: TableViewerBase):
    """Run plt.hist"""
    table = viewer.current_table
    if table is None:
        return

    _dialogs.hist(
        ax={"bind": table.plt.gca()},
        table={"bind": table},
        alpha={"min": 0, "max": 1, "step": 0.05},
        histtype={
            "choices": ["bar", "step", "stepfilled", "barstacked"],
            "value": "bar",
        },
        parent=viewer._qwidget,
    )


def swarmplot(viewer: TableViewerBase):
    """Run sns.swarmplot"""
    return _plot_sns(viewer, _dialogs.swarmplot)


def barplot(viewer: TableViewerBase):
    """Run sns.barplot"""
    return _plot_sns(viewer, _dialogs.barplot)


def boxplot(viewer: TableViewerBase):
    """Run sns.boxplot"""
    return _plot_sns(viewer, _dialogs.boxplot)


def boxenplot(viewer: TableViewerBase):
    """Run sns.boxenplot"""
    return _plot_sns(viewer, _dialogs.boxenplot)


def new_figure(viewer: TableViewerBase):
    """New figure canvas"""
    return viewer.current_table.plt.new_widget()


def _plot_xy(viewer: TableViewerBase, dialog):
    table = viewer.current_table
    if table is None:
        return

    dialog(
        ax={"bind": table.plt.gca()},
        x={"format": "iloc"},
        y={"format": "iloc"},
        table={"bind": table},
        alpha={"min": 0, "max": 1, "step": 0.05},
        parent=viewer._qwidget,
    )


def _plot_sns(viewer: TableViewerBase, dialog):
    table = viewer.current_table
    if table is None:
        return

    names, csel = _get_selected_ranges_and_column_names(table)

    # infer x, y
    if len(names) == 0:
        raise ValueError("Table must have at least one column.")
    elif len(names) == 1:
        x = {"bind": None}
        y = {"bind": None}
    else:
        for i, dtype in enumerate(table.data.dtypes):
            if dtype == "categorical":
                x = {"choices": names, "value": names[i], "nullable": True}
                j = 0 if i > 0 else 1
                y = {"choices": names, "value": names[j], "nullable": True}
                break
        else:
            x = {"choices": names, "value": None, "nullable": True}
            y = {"choices": names, "value": None, "nullable": True}

    if dialog(
        ax={"bind": table.plt.gca()},
        x=x,
        y=y,
        table={"bind": table},
        csel={"bind": csel},
        hue={"choices": names, "nullable": True},
        parent=viewer._qwidget,
    ):
        table.plt.draw()


class PlotInfo(NamedTuple):
    names: list[Hashable]
    columns: slice


def _get_selected_ranges_and_column_names(
    table: TableBase,
) -> PlotInfo:
    sels = table.selections
    if len(sels) == 1 and _selection_area(sels[0]) == 1:
        nrow = len(table.index)
        infos = PlotInfo(
            names=list(table.columns),
            columns=slice(0, nrow),
        )
    else:
        names = []
        sl = sels[0][0]
        columns = table.columns
        for sel in sels:
            if sel[0] == sl:
                csel = sel[1]
                for i in range(csel.start, csel.stop):
                    names.append(columns[i])
            else:
                raise ValueError("Selections must be in the same rows")
        infos = PlotInfo(names=names, columns=sl)

    return infos


def _selection_area(sel: tuple[slice, slice]) -> int:
    return (sel[0].stop - sel[0].start) * (sel[1].stop - sel[1].start)


del NamedTuple
