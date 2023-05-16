from tabulous import TableViewer
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

@pytest.mark.parametrize("fname", ["add_table", "add_spreadsheet"])
def test_undo_set_data_table(fname, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = getattr(viewer, fname)({"a": [1, 2, 3]})
    table.data = {"b": [1, 2, 3, 4, 5]}
    assert table.data.columns == ["b"]
    assert table.data.shape == (5, 1)
    table.undo_manager.undo()
    assert table.data.columns == ["a"]
    assert table.data.shape == (3, 1)
    table.undo_manager.redo()
    assert table.data.columns == ["b"]
    assert table.data.shape == (5, 1)

def test_undo_set_data_groupby(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [1, 2, 1, 2, 2]})
    df2 = pd.DataFrame({"a": [5, 6, 7, 8, 9], "b": [1, 2, 1, 1, 2]})
    group = df.groupby("b")
    group2 = df2.groupby("b")
    table = viewer.add_groupby(group)
    table.data = group2
    assert_frame_equal(table.data.count(), group2.count())

    table.undo_manager.undo()
    assert_frame_equal(table.data.count(), group.count())

    table.undo_manager.redo()
    assert_frame_equal(table.data.count(), group2.count())

def test_row_span_undo_redo(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet({"a": [1, 2, 3], "b": [1, 2, 3], "c": [0, 0, 0]})
    s = table.index.span[0]
    table.index.span[1] = s + 10
    assert table.index.span == [s, s + 10, s]
    table.index.remove(1)
    assert table.index.span == [s, s]
    table.undo_manager.undo()
    assert table.index.span == [s, s + 10, s]
    table.undo_manager.redo()
    assert table.index.span == [s, s]
    table.undo_manager.undo()
    assert table.index.span == [s, s + 10, s]

def test_column_span_undo_redo(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet({"a": [1, 2, 3], "b": [1, 2, 3], "c": [0, 0, 0]})
    s = table.columns.span[0]
    table.columns.span[1] = s + 10
    assert table.columns.span == [s, s + 10, s]
    table.columns.remove(1)
    assert table.columns.span == [s, s]
    table.undo_manager.undo()
    assert table.columns.span == [s, s + 10, s]
    table.undo_manager.redo()
    assert table.columns.span == [s, s]
    table.undo_manager.undo()
    assert table.columns.span == [s, s + 10, s]
