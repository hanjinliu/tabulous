from typing import List
import pandas as pd
from ..._magicgui import dialog_factory
from ...types import TableData


@dialog_factory
def summarize_table(df: TableData, methods: List[str]):
    return df.agg(methods)


@dialog_factory
def groupby(df: TableData, by: List[str]):
    return df.groupby(by)


@dialog_factory
def hconcat(viewer, names: List[str]):
    dfs = [viewer.tables[name].data for name in names]
    return pd.concat(dfs, axis=0)


@dialog_factory
def vconcat(viewer, names: List[str]):
    dfs = [viewer.tables[name].data for name in names]
    return pd.concat(dfs, axis=1)


@dialog_factory
def pivot(df: TableData, index: str, columns: str, values: str):
    return df.pivot(index=index, columns=columns, values=values)


@dialog_factory
def melt(df: TableData, id_vars: List[str]):
    return pd.melt(df, id_vars)


@dialog_factory
def query(df: TableData, expr: str):
    return df.query(expr)
