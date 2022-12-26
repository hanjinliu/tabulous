from tabulous import TableViewerWidget
from tabulous.widgets import Table
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest


def assert_table_proxy(table: Table, other: pd.DataFrame):
    return assert_frame_equal(table.data[table.proxy.as_indexer()], other)

def shuffled_arange(n: int, seed=0) -> np.ndarray:
    arr = np.arange(n)
    rng = np.random.default_rng(seed)
    rng.shuffle(arr)
    return arr

@pytest.mark.parametrize("n", [0, 7, 14, 20])
def test_simple_filter(n):
    viewer = TableViewerWidget(show=False)
    table = viewer.add_table({"a": shuffled_arange(20), "b": np.zeros(20)})
    assert table.table_shape == (20, 2)
    table.proxy.set(table.data["a"] < n)
    assert table.table_shape == (n, 2)
    table.proxy.reset()
    assert table.table_shape == (20, 2)

def test_function_filter():
    viewer = TableViewerWidget(show=False)
    table = viewer.add_table({"a": shuffled_arange(20), "b": np.zeros(20)})
    filter_func = lambda df: df["a"] < np.median(df["a"])
    table.proxy.set(filter_func)
    assert table.table_shape == (10, 2)
    assert_table_proxy(table, table.data[filter_func(table.data)])
    table.data = {"a": np.sin(shuffled_arange(30)), "val0": np.zeros(30), "val1": np.ones(30)}
    assert table.table_shape == (30, 3)
    assert_table_proxy(table, table.data)
    table.proxy.set(filter_func)
    assert table.table_shape == (15, 3)
    assert_table_proxy(table, table.data[filter_func(table.data)])
    table.proxy.set(None)
    assert table.table_shape == (30, 3)
    assert_table_proxy(table, table.data)


def test_expr_filter():
    viewer = TableViewerWidget(show=False)
    df = pd.DataFrame({"a": shuffled_arange(20), "b": shuffled_arange(20)**2})
    table = viewer.add_table(df)
    repr(table.proxy)  # check that it works
    table.proxy.filter("a<4")
    assert_table_proxy(table, df[df["a"] < 4])

    # check filter is initialized before updated
    table.proxy.filter("a<6")
    assert_table_proxy(table, df[df["a"] < 6])

    table.proxy.filter("a>6")
    assert_table_proxy(table, df[df["a"] > 6])

    table.proxy.filter("a<=6")
    assert_table_proxy(table, df[df["a"] <= 6])

    table.proxy.filter("a>=6")
    assert_table_proxy(table, df[df["a"] >= 6])

    table.proxy.filter("a==6")
    assert_table_proxy(table, df[df["a"] == 6])

    table.proxy.filter("(5<a)&(b<100)")
    assert_table_proxy(table, df[(5 < df["a"]) & (df["b"] < 100)])

def test_simple_sort():
    viewer = TableViewerWidget(show=False)
    table = viewer.add_table({"a": shuffled_arange(20), "b": np.zeros(20)})
    assert table.table_shape == (20, 2)
    table.proxy.set(table.data["a"].argsort())
    assert table.table_shape == (20, 2)
    assert np.all(table.data_shown["a"] == np.arange(20))
    table.proxy.reset()
    assert table.table_shape == (20, 2)

def test_function_sort():
    viewer = TableViewerWidget(show=False)
    table = viewer.add_table({"a": shuffled_arange(20), "b": np.zeros(20)})
    sort_func = lambda df: df["a"].argsort()
    table.proxy.set(sort_func)
    assert table.table_shape == (20, 2)
    assert np.all(table.data_shown["a"] == np.arange(20))
    table.data = {"a": shuffled_arange(30), "val0": np.zeros(30), "val1": np.ones(30)}
    assert table.table_shape == (30, 3)
    assert np.all(table.data_shown["a"] == shuffled_arange(30))
    table.proxy.set(sort_func)
    assert table.table_shape == (30, 3)
    assert np.all(table.data_shown["a"] == np.arange(30))
    table.proxy.set(None)
    assert table.table_shape == (30, 3)
    assert np.all(table.data_shown["a"] == shuffled_arange(30))

def test_sort_function():
    viewer = TableViewerWidget(show=False)
    df = pd.DataFrame(
        {"a": shuffled_arange(20), "b": shuffled_arange(20, seed=1)**2}
    )
    table = viewer.add_table(df)
    table.proxy.sort("a")
    assert np.all(table.data_shown["a"] == np.arange(20))
    table.proxy.sort("b")
    assert np.all(table.data_shown["b"] == np.arange(20)**2)
