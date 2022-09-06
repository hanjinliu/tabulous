from typing import List
from typing_extensions import Annotated
import numpy as np
import pandas as pd
from ..._magicgui import dialog_factory, Axes
from ...types import TableData


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


@dialog_factory
def plot(ax: Axes, x: str, y: List[str], data, alpha: float = 1.0):
    for ylabel in y:
        ydata: pd.Series = data[ylabel]
        if x is None:
            xdata = np.arange(len(ydata))
        else:
            xdata = data[x]
        ax.plot(xdata, ydata, alpha=alpha, label=ylabel, picker=True)
    return True


@dialog_factory
def scatter(ax: Axes, x: str, y: List[str], data, alpha: float = 1.0):
    for ylabel in y:
        ydata: pd.Series = data[ylabel]
        if x is None:
            xdata = np.arange(len(ydata))
        else:
            xdata = data[x]
        ax.scatter(xdata, ydata, alpha=alpha, label=ylabel, picker=True)
    return True


@dialog_factory
def errorbar(ax: Axes, x: str, y: str, yerr: str, data, alpha: float = 1.0):
    if x is None:
        xdata = np.arange(len(y))
    else:
        xdata = data[x]
    ax.errorbar(
        xdata, data[y], yerr=data[yerr], alpha=alpha, fmt="o", label=y, picker=True
    )
    return True


@dialog_factory
def hist(
    ax: Axes,
    y,
    data,
    bins: int = 10,
    alpha: float = 1.0,
    density: bool = False,
    histtype: str = "bar",
):
    for _y in y:
        ydata = data[_y]
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


@dialog_factory
def swarmplot(
    ax: Axes,
    x: str,
    y: str,
    data,
    hue: str = None,
    dodge: bool = False,
    alpha: Annotated[float, {"min": 0.0, "max": 1.0}] = 1.0,
):
    import seaborn as sns

    sns.swarmplot(
        x=x, y=y, data=data, hue=hue, dodge=dodge, alpha=alpha, ax=ax, picker=True
    )
    return True


@dialog_factory
def barplot(
    ax: Axes,
    x: str,
    y: str,
    data,
    hue: str = None,
    dodge: bool = False,
    alpha: Annotated[float, {"min": 0.0, "max": 1.0}] = 1.0,
):
    import seaborn as sns

    sns.barplot(
        x=x, y=y, data=data, hue=hue, dodge=dodge, alpha=alpha, ax=ax, picker=True
    )
    ax.axhline(0, color="gray", lw=0.5, alpha=0.5, zorder=-1)
    return True


@dialog_factory
def boxplot(
    ax: Axes,
    x: str,
    y: str,
    data,
    hue: str = None,
    dodge: bool = False,
):
    import seaborn as sns

    sns.boxplot(x=x, y=y, data=data, hue=hue, dodge=dodge, ax=ax)
    return True


@dialog_factory
def boxenplot(
    ax: Axes,
    x: str,
    y: str,
    data,
    hue: str = None,
    dodge: bool = False,
):
    import seaborn as sns

    sns.boxenplot(x=x, y=y, data=data, hue=hue, dodge=dodge, ax=ax, picker=True)
    return True
