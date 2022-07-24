from tabulous import TableViewerWidget
import numpy as np
from numpy import testing

def assert_equal(a, b):
    return testing.assert_equal(np.asarray(a), np.asarray(b))

def test_copy_and_paste_on_table():
    viewer = TableViewerWidget(show=False)
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

    sl_src = (slice(3, 5), slice(1, 3))
    sl_dst = (slice(2, 4), slice(0, 2))
    viewer.copy_data([sl_src])
    old_value = table.data.iloc[sl_dst].copy()
    copied = table.data.iloc[sl_src].copy()
    viewer.paste_data([sl_dst])
    assert_equal(table.data.iloc[sl_dst], copied)

    table.undo_manager.undo()
    assert_equal(table.data.iloc[sl_dst], old_value)


    sl_src = (slice(3, 5), slice(1, 3))
    sl_dst = (slice(2, 4), slice(0, 2))
    viewer.copy_data([sl_src])
    old_value = table.data.iloc[sl_dst].copy()
    copied = table.data.iloc[sl_src].copy()
    viewer.paste_data([(2, 0)])  # paste with single cell selection
    assert_equal(table.data.iloc[sl_dst], copied)

    table.undo_manager.undo()
    assert_equal(table.data.iloc[sl_dst], old_value)
