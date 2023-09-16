from tabulous import TableViewer
from tabulous.widgets import Table
import numpy as np
from numpy.testing import assert_equal
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
def test_simple_filter(n, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table({"a": shuffled_arange(20), "b": np.zeros(20)})
    assert table.table_shape == (20, 2)
    table.proxy.set(table.data["a"] < n)
    assert table.table_shape == (n, 2)
    table.proxy.reset()
    assert table.table_shape == (20, 2)

def test_function_filter(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
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


def test_expr_filter(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
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

def test_simple_sort(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table({"a": shuffled_arange(20), "b": np.zeros(20)})
    assert table.table_shape == (20, 2)
    table.proxy.set(table.data["a"].argsort())
    assert table.table_shape == (20, 2)
    assert np.all(table.data_shown["a"] == np.arange(20))
    table.proxy.reset()
    assert table.table_shape == (20, 2)

def test_function_sort(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
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

def test_sort_function(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    df = pd.DataFrame(
        {"a": shuffled_arange(20), "b": shuffled_arange(20, seed=1)**2}
    )
    table = viewer.add_table(df)
    table.proxy.sort("a")
    assert np.all(table.data_shown["a"] == np.arange(20))
    table.proxy.sort("b")
    assert np.all(table.data_shown["b"] == np.arange(20)**2)

def test_header_update(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table({"a": np.arange(10), "b": np.zeros(10)}, editable=True)
    table.proxy.filter("a % 2 == 0")
    table.index[2] = "x"
    assert list(table.index)== [0, 2, "x", 6, 8]
    assert list(table.data.index)== [0, 1, 2, 3, "x", 5, 6, 7, 8, 9]
    table.undo_manager.undo()
    assert list(table.index)== [0, 2, 4, 6, 8]
    assert list(table.data.index)== [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    table.undo_manager.redo()
    assert list(table.index)== [0, 2, "x", 6, 8]
    assert list(table.data.index)== [0, 1, 2, 3, "x", 5, 6, 7, 8, 9]
    table.proxy.reset()
    assert list(table.index)== [0, 1, 2, 3, "x", 5, 6, 7, 8, 9]
    assert list(table.data.index)== [0, 1, 2, 3, "x", 5, 6, 7, 8, 9]

def test_header_buttons(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table({"a": shuffled_arange(10), "b": np.arange(10)}, editable=True)
    table.proxy.sort(by="a")
    assert {0} == set(table._qwidget._header_widgets().keys())
    table.undo_manager.undo()
    assert set() == set(table._qwidget._header_widgets().keys())
    table.undo_manager.redo()
    assert {0} == set(table._qwidget._header_widgets().keys())
    table.proxy.add_filter_buttons(columns="b")
    assert {1} == set(table._qwidget._header_widgets().keys())
    table.undo_manager.undo()
    assert {0} == set(table._qwidget._header_widgets().keys())
    table.undo_manager.redo()
    assert {1} == set(table._qwidget._header_widgets().keys())

def test_header_buttons_with_insert(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet(
        {"a": np.arange(10), "b": shuffled_arange(10), "c": np.arange(10), "d": np.arange(10)},
    )
    table.proxy.sort(by=["b", "c"])
    sorted_index = list(table.index)

    assert {1, 2} == set(table._qwidget._header_widgets().keys())
    assert sorted_index == list(table.index)
    table.columns.insert(at=3, count=2)
    assert {1, 2} == set(table._qwidget._header_widgets().keys())
    assert sorted_index == list(table.index)
    table.columns.insert(at=1, count=2)
    assert {3, 4} == set(table._qwidget._header_widgets().keys())
    assert sorted_index == list(table.index)
    table.undo_manager.undo()
    assert {1, 2} == set(table._qwidget._header_widgets().keys())
    assert sorted_index == list(table.index)
    table.undo_manager.redo()
    assert {3, 4} == set(table._qwidget._header_widgets().keys())
    assert sorted_index == list(table.index)


def test_header_buttons_with_remove(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet(
        {"a": shuffled_arange(10), "b": np.arange(10), "c": np.arange(10)[::-1], "d": np.arange(10)},
    )
    table.proxy.sort(by=["b", "c"])
    sorted_index = list(table.index)

    assert {1, 2} == set(table._qwidget._header_widgets().keys())
    assert sorted_index == list(table.index)
    table.columns.remove(at=3, count=1)
    assert {1, 2} == set(table._qwidget._header_widgets().keys())
    assert sorted_index == list(table.index)
    table.columns.remove(at=0, count=2)
    assert {0} == set(table._qwidget._header_widgets().keys())
    assert list(range(10))[::-1] == list(table.index)
    table.undo_manager.undo()
    assert {1, 2} == set(table._qwidget._header_widgets().keys())
    assert sorted_index == list(table.index)
    table.undo_manager.redo()
    assert {0} == set(table._qwidget._header_widgets().keys())
    assert list(range(10))[::-1] == list(table.index)

def test_sort_and_filter_switched(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet(
        {"a": shuffled_arange(10), "b": np.arange(10), "c": np.arange(10)[::-1], "d": np.arange(10)},
    )
    table.proxy.sort(by="b")
    assert {1} == set(table._qwidget._header_widgets().keys())
    table.proxy.add_filter_buttons(columns="c")
    assert {2} == set(table._qwidget._header_widgets().keys())
    table.undo_manager.undo()
    assert {1} == set(table._qwidget._header_widgets().keys())
    table.undo_manager.redo()
    assert {2} == set(table._qwidget._header_widgets().keys())

def test_composing_sort(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet(
        {"a": [3, 2, 1, 3, 2, 1], "b": [2, 2, 2, 1, 1, 1]},
    )
    table.proxy.sort(by="a")
    assert_equal(table.data_shown["a"].values, [1, 1, 2, 2, 3, 3])
    assert_equal(table.data_shown["b"].values, [2, 1, 2, 1, 2, 1])
    table.proxy.sort(by="b", compose=True)
    assert_equal(table.data_shown["a"].values, [1, 1, 2, 2, 3, 3])
    assert_equal(table.data_shown["b"].values, [1, 2, 1, 2, 1, 2])

def test_column_filter(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet(
        {"a": [3, 2], "b": [2, 2], "ab": [4, 3]},
    )
    table.columns.filter.startswith("a")
    assert_equal(table.data_shown["a"].values, [3, 2])
    assert_equal(table.data_shown["ab"].values, [4, 3])
    assert "b" not in table.data_shown.columns
    table.columns.filter.isin(["a", "b"])
    assert_equal(table.data_shown["a"].values, [3, 2])
    assert_equal(table.data_shown["b"].values, [2, 2])
    assert "ab" not in table.data_shown.columns
    table.columns.filter.clear()
    assert list(table.data_shown.columns) == ["a", "b", "ab"]

def test_column_filter_with_sort(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet(
        {"a": [3, 2], "b": [2, 2], "ba": [4, 3]},
    )
    table.proxy.sort(by="a")
    table.columns.filter.startswith("b")
    assert_equal(table.data_shown["ba"], [3, 4])
    table.undo_manager.undo()
    assert list(table.data_shown.columns) == ["a", "b", "ba"]
    assert_equal(table.data_shown["ba"], [3, 4])
    table.undo_manager.undo()
    assert_equal(table.data_shown["ba"], [4, 3])
