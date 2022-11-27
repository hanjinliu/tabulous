from typing import List, cast
from typing_extensions import Annotated
import weakref
import logging
import numpy as np
import pandas as pd

# NOTE: Axes should be imported here!
from tabulous.widgets import TableBase
from tabulous.types import TableData
from tabulous._selection_op import SelectionOperator
from tabulous._magicgui import dialog_factory, dialog_factory_mpl, Axes


logger = logging.getLogger(__name__)


@dialog_factory
def summarize_table(df: TableData, methods: List[str], new_table: bool = False):
    return df.agg(methods), new_table


@dialog_factory
def groupby(df: TableData, by: List[str]):
    return df.groupby(by)


@dialog_factory
def concat(
    viewer, names: List[str], axis: int, ignore_index: bool = False
) -> TableData:
    dfs = [viewer.tables[name].data for name in names]
    return pd.concat(dfs, axis=axis, ignore_index=ignore_index)


@dialog_factory
def pivot(df: TableData, index: str, columns: str, values: str) -> TableData:
    return df.pivot(index=index, columns=columns, values=values)


@dialog_factory
def melt(df: TableData, id_vars: List[str]) -> TableData:
    return pd.melt(df, id_vars)


@dialog_factory
def sort(df: TableData, by: List[str], ascending: bool = True) -> TableData:
    return df.sort_values(by=by, ascending=ascending)


@dialog_factory_mpl
def plot(
    ax: Axes,
    x: SelectionOperator,
    y: SelectionOperator,
    table,
    alpha: float = 1.0,
    ref: bool = False,
):
    table = cast(TableBase, table)
    data = table.data
    xdata, ydata_all, reactive_ranges = _normalize_2d_plot(data, x, y)

    for y_, ydata in ydata_all.items():
        (artist,) = ax.plot(xdata, ydata, alpha=alpha, label=y_, picker=True)
        if not ref:
            continue
        _ref = weakref.ref(artist)
        _mpl_widget = weakref.ref(table.plt.gcw())

        logger.debug(f"Connecting plt.plot update callback at {y_!r}")

        def _on_data_updated(info):
            _artist = _ref()
            _plt = _mpl_widget()
            if _artist is None:
                table.events.data.disconnect(_on_data_updated)
                logger.debug(f"Disconnecting plt.plot update callback at {y_!r}")
                return
            try:
                _ydata = table.data[y_]
                if x is None:
                    _artist.set_ydata(_ydata)
                else:
                    _xdata = table.data[xdata.name]
                    _artist.set_data(_xdata, _ydata)
                _plt.draw()
            except RuntimeError as e:
                if str(e).startswith("wrapped C/C++ object of"):
                    table.events.data.disconnect(_on_data_updated)
                    logger.debug(f"Disconnecting plt.plot update callback at {y_!r}")

        table.events.data.mloc(reactive_ranges).connect(_on_data_updated)

    table.plt.draw()
    return artist


@dialog_factory_mpl
def scatter(
    ax: Axes,
    x: SelectionOperator,
    y: SelectionOperator,
    table,
    alpha: float = 1.0,
    ref: bool = False,
):
    table = cast(TableBase, table)
    data = table.data

    xdata, ydata_all, reactive_ranges = _normalize_2d_plot(data, x, y)

    for y_, ydata in ydata_all.items():
        artist = ax.scatter(xdata, ydata, alpha=alpha, label=y_, picker=True)
        if not ref:
            continue
        _ref = weakref.ref(artist)
        _mpl_widget = weakref.ref(table.plt.gcw())

        def _on_data_updated():
            _artist = _ref()
            _plt = _mpl_widget()
            if _artist is None:
                table.events.data.disconnect(_on_data_updated)
                return
            try:
                _ydata = table.data[y_]
                if x is None:
                    _xdata = np.arange(len(_ydata))
                else:
                    _xdata = table.data[xdata.name]
                _artist.set_offsets(np.stack([_xdata, _ydata], axis=1))
                _plt.draw()
            except RuntimeError as e:
                if str(e).startswith("wrapped C/C++ object of"):
                    table.events.data.disconnect(_on_data_updated)

        table.events.data.mloc(reactive_ranges).connect(_on_data_updated)

    table.plt.draw()
    return True


@dialog_factory_mpl
def errorbar(
    ax: Axes,
    x: SelectionOperator,
    y: SelectionOperator,
    yerr: SelectionOperator,
    table,
    alpha: float = 1.0,
):
    table = cast(TableBase, table)
    data = table.data
    ydata = y.operate(data)
    yerrdata = yerr.operate(data)
    if x is None:
        xdata = np.arange(len(ydata))
    else:
        xdata = x.operate(data)

    ax.errorbar(
        xdata,
        y=ydata,
        yerr=yerrdata,
        alpha=alpha,
        fmt="o",
        label=y,
        picker=True,
    )

    table.plt.draw()
    return True


@dialog_factory_mpl
def hist(
    ax: Axes,
    y: SelectionOperator,
    table,
    bins: int = 10,
    alpha: float = 1.0,
    density: bool = False,
    histtype: str = "bar",
):
    table = cast(TableBase, table)
    data = table.data

    if y is None:
        raise ValueError("Y must be set.")

    ydata_all = data.iloc[y.as_iloc_slices(data)]

    for _y, ydata in ydata_all.items():
        ax.hist(
            ydata,
            bins=bins,
            alpha=alpha,
            density=density,
            label=_y,
            histtype=histtype,
            picker=True,
        )
    ax.axhline(0, color="gray", lw=0.5, alpha=0.5, zorder=-1)
    table.plt.draw()
    return True


@dialog_factory_mpl
def swarmplot(
    ax: Axes,
    x: str,
    y: str,
    table,
    csel,
    hue: str = None,
    dodge: bool = False,
    alpha: Annotated[float, {"min": 0.0, "max": 1.0}] = 1.0,
):
    import seaborn as sns

    table = cast(TableBase, table)
    data = table.data[csel]
    sns.swarmplot(
        x=x, y=y, data=data, hue=hue, dodge=dodge, alpha=alpha, ax=ax, picker=True
    )
    table.plt.draw()
    return True


@dialog_factory_mpl
def barplot(
    ax: Axes,
    x: str,
    y: str,
    table,
    csel,
    hue: str = None,
    dodge: bool = False,
    alpha: Annotated[float, {"min": 0.0, "max": 1.0}] = 1.0,
):
    import seaborn as sns

    table = cast(TableBase, table)
    data = table.data[csel]
    sns.barplot(
        x=x, y=y, data=data, hue=hue, dodge=dodge, alpha=alpha, ax=ax, picker=True
    )
    ax.axhline(0, color="gray", lw=0.5, alpha=0.5, zorder=-1)
    table.plt.draw()
    return True


@dialog_factory_mpl
def boxplot(
    ax: Axes,
    x: str,
    y: str,
    table,
    csel,
    hue: str = None,
    dodge: bool = False,
):
    import seaborn as sns

    table = cast(TableBase, table)
    data = table.data[csel]
    sns.boxplot(x=x, y=y, data=data, hue=hue, dodge=dodge, ax=ax)
    table.plt.draw()
    return True


@dialog_factory_mpl
def boxenplot(
    ax: Axes,
    x: str,
    y: str,
    table,
    csel,
    hue: str = None,
    dodge: bool = False,
):
    import seaborn as sns

    table = cast(TableBase, table)
    data = table.data[csel]
    sns.boxenplot(x=x, y=y, data=data, hue=hue, dodge=dodge, ax=ax, picker=True)
    table.plt.draw()
    return True


@dialog_factory
def choose_one(choice: str):
    return choice


def _normalize_2d_plot(data: pd.DataFrame, x: SelectionOperator, y: SelectionOperator):
    if y is None:
        raise ValueError("Y must be set.")

    yslice = y.as_iloc_slices(data)
    ydata_all = data.iloc[yslice]

    reactive_ranges = [yslice]

    if x is None:
        xdata = np.arange(len(ydata_all))
    else:
        xslice = x.as_iloc_slices(data)
        reactive_ranges.append(xslice)
        if xslice[1].start != xslice[1].stop - 1:
            raise ValueError("X must be a single column.")
        xdata = data.iloc[xslice[0], xslice[1].start]

    return xdata, ydata_all, reactive_ranges
