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

def test_setting_cell_out_of_bound():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet()
    qtable = cast(QSpreadSheet, viewer.tables[0].native)

    qtable.setDataFrameValue(2, 1, "x")
    assert sheet.data.shape == (3, 2)
    qtable.setDataFrameValue(2, 3, "y")
    assert sheet.data.shape == (3, 4)
    qtable.setDataFrameValue(1, 1, "z")
    assert sheet.data.shape == (3, 4)

    qtable.undo()
    assert sheet.data.shape == (3, 4)
    qtable.undo()
    assert sheet.data.shape == (3, 2)
    qtable.undo()
    assert sheet.data.shape == (0, 0)

def test_setting_header_out_of_bound():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet()
    qtable = cast(QSpreadSheet, viewer.tables[0].native)

    qtable.setHorizontalHeaderValue(1, "col1")
    assert sheet.data.shape == (0, 2)
    qtable.setHorizontalHeaderValue(2, "col2")
    assert sheet.data.shape == (0, 3)
    qtable.setVerticalHeaderValue(2, "row2")
    assert sheet.data.shape == (3, 3)

    qtable.undo()
    assert sheet.data.shape == (0, 3)
    qtable.undo()
    assert sheet.data.shape == (0, 2)
    qtable.undo()
    assert sheet.data.shape == (0, 0)
