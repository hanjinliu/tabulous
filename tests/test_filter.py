from tabulous import TableViewerWidget
from tabulous.widgets import Table
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest


def assert_table_filter(table: Table, other: pd.DataFrame):
    if table.filter:
        return assert_frame_equal(table.data[table.filter.array()], other)
    else:
        return assert_frame_equal(table.data, other)

@pytest.mark.parametrize("n", [0, 7, 14, 20])
def test_simple_filter(n):
    viewer = TableViewerWidget(show=False)
    table = viewer.add_table({"a": np.arange(20), "b": np.zeros(20)})
    assert table.table_shape == (20, 2)
    table.filter = table.data["a"] < n
    assert table.table_shape == (n, 2)
    table.filter = None
    assert table.table_shape == (20, 2)

def test_function_filter():
    viewer = TableViewerWidget(show=False)
    table = viewer.add_table({"a": np.arange(20), "b": np.zeros(20)})
    filter_func = lambda df: df["a"] < np.median(df["a"])
    table.filter = filter_func
    assert table.table_shape == (10, 2)
    assert_table_filter(table, table.data[filter_func(table.data)])
    table.data = {"a": np.sin(np.arange(30)), "val0": np.zeros(30), "val1": np.ones(30)}
    assert table.table_shape == (30, 3)
    assert_table_filter(table, table.data)
    table.filter = filter_func
    assert table.table_shape == (15, 3)
    assert_table_filter(table, table.data[filter_func(table.data)])
    table.filter = None
    assert table.table_shape == (30, 3)
    assert_table_filter(table, table.data)


def test_filter_proxy():
    viewer = TableViewerWidget(show=False)
    df = pd.DataFrame({"a": np.arange(20), "b": np.arange(20)**2})
    table = viewer.add_table(df)
    repr(table.filter)  # check that it works
    table.filter["a"] < 4
    assert_table_filter(table, df[df["a"] < 4])

    # check filter is initialized before updated
    table.filter["a"] < 6
    assert_table_filter(table, df[df["a"] < 6])

    table.filter["a"] > 6
    assert_table_filter(table, df[df["a"] > 6])

    table.filter["a"] <= 6
    assert_table_filter(table, df[df["a"] <= 6])

    table.filter["a"] >= 6
    assert_table_filter(table, df[df["a"] >= 6])

    table.filter["a"] == 6
    assert_table_filter(table, df[df["a"] == 6])

    (5 < table.filter["a"]) & (table.filter["b"] < 100)
    assert_table_filter(table, df[(5 < df["a"]) & (df["b"] < 100)])
