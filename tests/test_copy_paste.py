from tabulous import TableViewer
import numpy as np
from numpy import testing

def assert_equal(a, b):
    return testing.assert_equal(np.asarray(a), np.asarray(b))

def test_copy_and_paste_1x1(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table({
        "a": [0, 1, 2, 3, 4],
        "b": [2, 4, 6, 8, 10],
        "c": [-1, -1, -1, -1, -1],
    }, editable=True)
    sl_src = (2, 2)
    sl_dst = (1, 1)
    viewer.copy_data([sl_src])  # copy -1
    old_value = table.data.iloc[sl_dst]
    copied = table.data.iloc[sl_src]
    viewer.paste_data([sl_dst])  # paste -1
    assert table.data.iloc[sl_dst] == copied

    table.undo_manager.undo()
    assert table.data.iloc[sl_dst] == old_value


def test_copy_and_paste_same_shape(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table({
        "a": [0, 1, 2, 3, 4],
        "b": [2, 4, 6, 8, 10],
        "c": [-1, -1, -1, -1, -1],
    }, editable=True)

    sl_src = (slice(3, 5), slice(1, 3))
    sl_dst = (slice(2, 4), slice(0, 2))
    viewer.copy_data([sl_src])
    old_value = table.data.iloc[sl_dst].copy()
    copied = table.data.iloc[sl_src].copy()
    viewer.paste_data([sl_dst])
    assert_equal(table.data.iloc[sl_dst], copied)

    table.undo_manager.undo()
    assert_equal(table.data.iloc[sl_dst], old_value)


def test_copy_array_and_paste_single(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table({
        "a": [0, 1, 2, 3, 4],
        "b": [2, 4, 6, 8, 10],
        "c": [-1, -1, -1, -1, -1],
    }, editable=True)

    sl_src = (slice(3, 5), slice(1, 3))
    sl_dst = (slice(2, 4), slice(0, 2))
    viewer.copy_data([sl_src])
    old_value = table.data.iloc[sl_dst].copy()
    copied = table.data.iloc[sl_src].copy()
    viewer.paste_data([(2, 0)])  # paste with single cell selection
    assert_equal(table.data.iloc[sl_dst], copied)

    table.undo_manager.undo()
    assert_equal(table.data.iloc[sl_dst], old_value)

def test_paste_with_column_selected(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet({
        "a": [0, 1, 2, 3, 4],
        "b": [2, 4, 6, 8, 10],
        "c": [-1, -1, -1, -1, -1],
    })

    viewer.copy_data([(slice(0, 5), slice(2, 3))])
    table._qwidget._qtable_view._selection_model.move_to(-1, 0)
    viewer.paste_data()
    assert_equal(table.data.iloc[:, 0], np.full(5, -1))

def test_paste_with_filter(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet({
        "a": [0, 1, 2, 3, 4],
        "b": ["a", "b", "c", "d", "e"],
        "c": ["x"] * 5,
    })
    viewer.copy_data([(slice(0, 3), slice(2, 3))])
    sheet.proxy.filter("a % 2 == 0")
    viewer.paste_data([(slice(0, 3), slice(1, 2))])
    assert_equal(sheet.data.iloc[:, 1], ["x", "b", "x", "d", "x"])
