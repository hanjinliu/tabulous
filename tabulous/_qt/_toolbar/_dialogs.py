from typing import List, cast
from typing_extensions import Annotated
import weakref
import logging
import numpy as np
import pandas as pd

# NOTE: Axes should be imported here!
from ..._magicgui import dialog_factory, dialog_factory_mpl, Axes
from ...widgets import TableBase
from ...types import TableData


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
    x: str,
    y: List[str],
    table,
    csel,
    alpha: float = 1.0,
    ref: bool = False,
):
    table = cast(TableBase, table)
    data = table.data
    if x is None:
        xdata = np.arange(len(ydata))
    else:
        xdata = data[x][csel]

    for y_ in y:
        ydata: pd.Series = data[y_][csel]
        (artist,) = ax.plot(xdata, ydata, alpha=alpha, label=y_, picker=True)
        if ref:
            _ref = weakref.ref(artist)
            _mpl_widget = weakref.ref(table.plt.gcw())

            logger.debug(f"Connecting plt.plot update callback at {y_!r}")

            @table.events.data.connect
            def _on_data_updated(info):
                _artist = _ref()
                _plt = _mpl_widget()
                if _artist is None or _plt is None:
                    table.events.data.disconnect(_on_data_updated)
                    logger.debug(f"Disconnecting plt.plot update callback at {y_!r}")
                    return
                xdata = table.data[x][csel]
                ydata = table.data[y_][csel]
                _artist.set_data(xdata, ydata)
                _plt.draw()

    return artist


@dialog_factory_mpl
def scatter(
    ax: Axes,
    x: str,
    y: List[str],
    table,
    csel,
    alpha: float = 1.0,
    ref: bool = False,
):
    table = cast(TableBase, table)
    data = table.data
    if x is None:
        xdata = np.arange(len(ydata))
    else:
        xdata = data[x][csel]

    for y_ in y:
        ydata: pd.Series = data[y_][csel]
        artist = ax.scatter(xdata, ydata, alpha=alpha, label=y_, picker=True)
        if ref:
            _ref = weakref.ref(artist)
            _mpl_widget = weakref.ref(table.plt.gcw())

            @table.events.data.connect
            def _on_data_updated():
                _artist = _ref()
                _plt = _mpl_widget()
                if _artist is None:
                    table.events.data.disconnect(_on_data_updated)
                    return
                xdata = table.data[x][csel]
                ydata = table.data[y_][csel]
                _artist.set_offsets(np.stack([xdata, ydata], axis=1))
                _plt.draw()

    return True


@dialog_factory_mpl
def errorbar(
    ax: Axes,
    x: str,
    y: str,
    yerr: str,
    table,
    csel,
    alpha: float = 1.0,
):
    table = cast(TableBase, table)
    data = table.data
    if x is None:
        xdata = np.arange(len(y))
    else:
        xdata = data[x][csel]
    ax.errorbar(
        xdata,
        data[y][csel],
        yerr=data[yerr][csel],
        alpha=alpha,
        fmt="o",
        label=y,
        picker=True,
    )

    return True


@dialog_factory_mpl
def hist(
    ax: Axes,
    y: List[str],
    table,
    csel,
    bins: int = 10,
    alpha: float = 1.0,
    density: bool = False,
    histtype: str = "bar",
):
    table = cast(TableBase, table)
    data = table.data
    for _y in y:
        ydata = data[_y][csel]
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
    return True


@dialog_factory
def choose_one(choice: str):
    return choice
