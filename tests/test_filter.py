from tabulous import TableViewer
import numpy as np
import pytest

@pytest.mark.parametrize("n", [0, 7, 14, 20])
def test_simple_filter(n):
    viewer = TableViewer(show=False)
    table = viewer.add_table({"a": np.arange(20), "b": np.zeros(20)})
    assert table.table_shape == (20, 2)
    table.filter = table.data["a"] < n
    assert table.table_shape == (n, 2)
    table.filter = None
    assert table.table_shape == (20, 2)
    
def test_function_filter():
    viewer = TableViewer(show=False)
    table = viewer.add_table({"a": np.arange(20), "b": np.zeros(20)})
    filter_func = lambda df: df["a"] < np.median(df["a"])
    table.filter = filter_func
    assert table.table_shape == (10, 2)
    table.data = {"a": np.sin(np.arange(30)), "val0": np.zeros(30), "val1": np.ones(30)}
    assert table.table_shape == (30, 3)
    table.filter = filter_func
    assert table.table_shape == (15, 3)
    table.filter = None
    assert table.table_shape == (30, 3)
