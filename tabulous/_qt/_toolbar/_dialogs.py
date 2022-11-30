from functools import partial
from typing import List, Union
from typing_extensions import Annotated
import logging
import numpy as np
import pandas as pd

# NOTE: Axes should be imported here!
from tabulous.widgets import TableBase
from tabulous.types import TableData
from tabulous._selection_op import SelectionOperator
from tabulous._magicgui import dialog_factory, dialog_factory_mpl, Axes

from ._plot_models import PlotModel, ScatterModel


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
    table: TableBase,
    alpha: float = 1.0,
    ref: bool = False,
):
    model = PlotModel(ax, x, y, table=table, alpha=alpha, ref=ref)
    model.add_data()
    table.plt.draw()
    return True


@dialog_factory_mpl
def scatter(
    ax: Axes,
    x: SelectionOperator,
    y: SelectionOperator,
    label: SelectionOperator,
    table: TableBase,
    alpha: float = 1.0,
    ref: bool = False,
):
    model = ScatterModel(
        ax, x, y, table=table, label_selection=label, alpha=alpha, ref=ref
    )
    model.add_data()
    table.plt.draw()
    return True


@dialog_factory_mpl
def errorbar(
    ax: Axes,
    x: SelectionOperator,
    y: SelectionOperator,
    xerr: SelectionOperator,
    yerr: SelectionOperator,
    label: SelectionOperator,
    table: TableBase,
    alpha: float = 1.0,
):
    data = table.data
    ydata = _operate_column(y, data)

    xerrdata = _operate_column(xerr, data, default=None)
    yerrdata = _operate_column(yerr, data, default=None)
    if xerrdata is None and yerrdata is None:
        raise ValueError("Either x-error or y-error must be set.")

    labeldata = _operate_column(label, data, default=None)
    if x is None:
        xdata = pd.Series(np.arange(len(ydata)), name="X")
    else:
        xdata = _operate_column(x, data)

    _errorbar = partial(ax.errorbar, alpha=alpha, fmt="o", picker=True)
    if labeldata is None:
        _errorbar(xdata, ydata, xerr=xerrdata, yerr=yerrdata, label=y)
    else:
        unique = labeldata.unique()
        for label_ in unique:
            spec = labeldata == label_
            _errorbar(
                xdata[spec],
                ydata[spec],
                xerr=xerrdata[spec],
                yerr=yerrdata[spec],
                label=label_,
            )

    table.plt.draw()
    return True


@dialog_factory_mpl
def hist(
    ax: Axes,
    y: SelectionOperator,
    table: TableBase,
    bins: int = 10,
    alpha: float = 1.0,
    density: bool = False,
    histtype: str = "bar",
):
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
    table: TableBase,
    csel,
    hue: str = None,
    dodge: bool = False,
    alpha: Annotated[float, {"min": 0.0, "max": 1.0}] = 1.0,
):
    import seaborn as sns

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
    table: TableBase,
    csel,
    hue: str = None,
    dodge: bool = False,
    alpha: Annotated[float, {"min": 0.0, "max": 1.0}] = 1.0,
):
    import seaborn as sns

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
    table: TableBase,
    csel,
    hue: str = None,
    dodge: bool = False,
):
    import seaborn as sns

    data = table.data[csel]
    sns.boxplot(x=x, y=y, data=data, hue=hue, dodge=dodge, ax=ax)
    table.plt.draw()
    return True


@dialog_factory_mpl
def boxenplot(
    ax: Axes,
    x: str,
    y: str,
    table: TableBase,
    csel,
    hue: str = None,
    dodge: bool = False,
):
    import seaborn as sns

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
        xdata = pd.Series(np.arange(len(ydata_all)), name="X")
    else:
        xslice = x.as_iloc_slices(data)
        reactive_ranges.append(xslice)
        if xslice[1].start != xslice[1].stop - 1:
            raise ValueError("X must be a single column.")
        xdata = data.iloc[xslice[0], xslice[1].start]

    return xdata, ydata_all, reactive_ranges


__void = object()


def _operate_column(
    op: Union[SelectionOperator, None],
    data: pd.DataFrame,
    default=__void,
) -> Union[pd.Series, None]:
    if op is None:
        if default is __void:
            raise ValueError("Wrong selection.")
        return default
    ds = op.operate(data)
    if isinstance(ds, pd.DataFrame):
        if len(ds.columns) != 1:
            raise ValueError("Operation must return a single column.")
        ds = ds.iloc[:, 0]
    return ds
