from tabulous import TableViewer
from tabulous._qt import QSpreadSheet
from typing import cast
import numpy as np

def assert_data_equal(a, b):
    a = np.array(a).tolist()
    b = np.array(b).tolist()
    assert len(a) == len(b), "length mismatch in the first dimension"
    for a0, b0 in zip(a, b):
        assert len(a0) == len(b0), "length mismatch in the second dimension"
        for a1, b1 in zip(a0, b0):
            assert a1 == b1, "value mismatch"

data = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

def test_insert():
    viewer = TableViewer(show=False)
    viewer.add_spreadsheet(data)
    qtable = cast(QSpreadSheet, viewer.tables[0].native)

    qtable.insertColumns(1, 1)
    assert_data_equal(qtable._data_raw, [["1", "", "2", "3"], ["4", "", "5", "6"], ["7", "", "8", "9"]])
    qtable.undo()
    assert_data_equal(qtable._data_raw, [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]])
    qtable.redo()
    assert_data_equal(qtable._data_raw, [["1", "", "2", "3"], ["4", "", "5", "6"], ["7", "", "8", "9"]])
    qtable.undo()

    qtable.insertRows(1, 1)
    assert_data_equal(qtable._data_raw, [["1", "2", "3"], ["", "", ""], ["4", "5", "6"], ["7", "8", "9"]])
    qtable.undo()
    assert_data_equal(qtable._data_raw, [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]])
    qtable.redo()
    assert_data_equal(qtable._data_raw, [["1", "2", "3"], ["", "", ""], ["4", "5", "6"], ["7", "8", "9"]])

def test_remove():
    viewer = TableViewer(show=False)
    viewer.add_spreadsheet(data)
    qtable = cast(QSpreadSheet, viewer.tables[0].native)

    qtable.removeColumns(1, 1)
    assert_data_equal(qtable._data_raw, [["1", "3"], ["4", "6"], ["7", "9"]])
    qtable.undo()
    assert_data_equal(qtable._data_raw, [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]])
    qtable.redo()
    assert_data_equal(qtable._data_raw, [["1", "3"], ["4", "6"], ["7", "9"]])
    qtable.undo()

    qtable.removeRows(1, 1)
    assert_data_equal(qtable._data_raw, [["1", "2", "3"], ["7", "8", "9"]])
    qtable.undo()
    assert_data_equal(qtable._data_raw, [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]])
    qtable.redo()
    assert_data_equal(qtable._data_raw, [["1", "2", "3"], ["7", "8", "9"]])
