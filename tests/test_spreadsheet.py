import pytest
from tabulous import TableViewer
from tabulous._qt import QSpreadSheet
from tabulous.types import ItemInfo
from typing import Callable, cast
import numpy as np
import pandas as pd
from unittest.mock import MagicMock

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
    assert list(sheet.data.columns) == ["A", "col1"]
    qtable.setHorizontalHeaderValue(2, "col2")
    assert sheet.data.shape == (0, 3)
    assert list(sheet.data.columns) == ["A", "col1", "col2"]
    qtable.setVerticalHeaderValue(2, "row2")
    assert sheet.data.shape == (3, 3)
    assert list(sheet.data.index) == [0, 1, "row2"]

    qtable.undo()
    assert sheet.data.shape == (0, 3)
    assert list(sheet.data.columns) == ["A", "col1", "col2"]
    qtable.undo()
    assert sheet.data.shape == (0, 2)
    assert list(sheet.data.columns) == ["A", "col1"]
    qtable.undo()
    assert sheet.data.shape == (0, 0)

@pytest.mark.parametrize("dtype", ["string", "int", "float"])
def test_column_dtype(dtype: str):
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 2, 3]})
    with pytest.raises(ValueError):
        sheet.dtypes["b"] = dtype
    sheet.dtypes["a"] = dtype
    assert sheet.data.dtypes["a"] == dtype

def test_column_dtype_validation():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 2, 3]})
    sheet.dtypes.set("a", "int")
    sheet.cell[0, 0] = 1
    with pytest.raises(ValueError):
        sheet.cell[0, 0] = "a"

    # validator should be reset
    del sheet.dtypes["a"]
    sheet.cell[0, 0] = "a"

def test_table_signal():
    viewer = TableViewer(show=False)
    table = viewer.add_spreadsheet(np.zeros((6, 6)))
    mock = MagicMock()
    table.events.data.connect(mock)
    mock.assert_not_called()
    table.cell[0, 0] = "1"
    mock.call_args.args[0].row == slice(0, 1)
    mock.call_args.args[0].column == slice(0, 1)

    table.cell[1, :] = "1"
    mock.call_args.args[0].row == 1
    mock.call_args.args[0].column == slice(None)

    table._qwidget.removeRows(2, 1)
    mock.call_args.args[0].row == slice(2, 3)
    mock.call_args.args[0].column == slice(None)
    mock.call_args.args[0].value == ItemInfo.DELETED
    table.undo_manager.undo()
    mock.call_args.args[0].row == slice(2, 3)
    mock.call_args.args[0].column == slice(None)
    mock.call_args.args[0].old_value == ItemInfo.INSERTED

    table._qwidget.removeColumns(2, 1)
    mock.call_args.args[0].row == slice(None)
    mock.call_args.args[0].column == slice(2, 3)
    mock.call_args.args[0].value == ItemInfo.DELETED
    table.undo_manager.undo()
    mock.call_args.args[0].row == slice(None)
    mock.call_args.args[0].column == slice(2, 3)
    mock.call_args.args[0].old_value == ItemInfo.INSERTED

def test_ranged_index_extension():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet(np.zeros((3, 3)))
    assert list(sheet.columns) == ["A", "B", "C"]
    sheet.cell[0, 3] = "0"
    assert list(sheet.columns) == ["A", "B", "C", "D"]
    sheet.columns[1] = "E"
    assert list(sheet.columns) == ["A", "E", "C", "D"]
    sheet.cell[0, 4] = "0"
    assert list(sheet.columns) == ["A", "E", "C", "D", "E_0"]
    sheet.cell[0, 6] = "0"
    assert list(sheet.columns) == ["A", "E", "C", "D", "E_0", "F", "G"]
