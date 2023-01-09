from unittest.mock import MagicMock
from tabulous import TableViewer
from tabulous.widgets import Table
import pandas as pd
import numpy as np
from magicgui import magicgui
from qtpy import QtWidgets as QtW
import pytest

from ._utils import edit_cell, selection_equal

df0 = pd.DataFrame({"a": [10, 20, 30], "b": [1.0, 1.1, 1.2]})
df1 = pd.DataFrame({"label": ["one", "two", "one"], "value": [1.0, 1.1, 1.2]})

@pytest.mark.parametrize("df", [df0, df1])
def test_display(df: pd.DataFrame):
    viewer = TableViewer(show=False)
    table = Table(df)
    viewer.add_layer(table)
    assert table.data is df
    assert table.data.columns is df.columns
    assert table.data.index is df.index
    assert table.table_shape == df.shape
    assert table.cell.text[0, 0] == str(df.iloc[0, 0])

@pytest.mark.parametrize("df", [df0, df1])
def test_editing_data(df: pd.DataFrame):
    viewer = TableViewer(show=False)
    table = Table(df)
    viewer.add_layer(table)
    edit_cell(table._qwidget, 0, 0, "11")
    assert str(df.iloc[0, 0]) == "11"

def test_copy():
    viewer = TableViewer(show=False)
    df = pd.DataFrame({"a": [1, 2, 3], "b": [0, 0, 0]})
    table = viewer.add_table(df, copy=True, editable=True)
    table.cell[0, 0] = "11"
    assert df.iloc[0, 0] == 1

    df = pd.DataFrame({"a": [1, 2, 3], "b": [0, 0, 0]})
    table = viewer.add_table(df, copy=False, editable=True)
    table.cell[0, 0] = "11"
    assert df.iloc[0, 0] == 11

def test_cell_interface():
    viewer = TableViewer(show=False)
    df = pd.DataFrame({"a": [1, 2, 3], "b": [0, 0, 0]})
    table = viewer.add_table(df, copy=True, editable=True)

    mock = MagicMock()
    table.events.data.connect(mock)
    mock.assert_not_called()
    table.cell[0, 0] = "11"
    mock.assert_called_once()

@pytest.mark.parametrize("df", [df0, df1])
def test_updating_data(df: pd.DataFrame):
    viewer = TableViewer(show=False)
    table = viewer.add_table(np.zeros((3, 3)))
    table.data = df
    assert str(table.data.iloc[0, 0]) == str(df.iloc[0, 0])

@pytest.mark.parametrize("df", [df0, df1])
def test_editing_original_data(df: pd.DataFrame):
    viewer = TableViewer(show=False)
    df = df.copy()
    table = viewer.add_table(df, copy=False, editable=True)
    table.data.iloc[0, 1] = -1.
    table.cell[1, 1] = "100.0"
    assert df.iloc[0, 1] == -1.
    assert df.iloc[1, 1] == 100.


def test_size_change():
    viewer = TableViewer(show=False)
    table = Table(np.zeros((30, 30)))
    viewer.add_layer(table)

    table.data = np.zeros((20, 20))
    assert table.table_shape == (20, 20)
    table.data = np.zeros((40, 40))
    assert table.table_shape == (40, 40)


def test_move_location():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)

    table.move_loc(1, "a")
    table.move_iloc(2, 1)

    with pytest.raises(IndexError):
        table.move_iloc(2, 5)

    with pytest.raises(IndexError):
        table.move_iloc(5, 2)

def test_assign():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)
    table.assign(c=[1, 2, 3])
    assert all(table.columns == ["a", "b", "c"])
    assert all(table.data["c"] == [1, 2, 3])

    table.assign(b=[True, False, True])
    assert all(table.columns == ["a", "b", "c"])
    assert all(table.data["b"] == [True, False, True])
    assert table.data.dtypes[1] == bool

def test_dual_view():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)

    table.view_mode = "horizontal"
    table.view_mode = "vertical"
    table.view_mode = "normal"
    table.view_mode = "vertical"
    table.view_mode = "horizontal"

    table.selections = [(slice(1, 2), slice(0, 2))]
    selection_equal(table.selections, [(slice(1, 2), slice(0, 2))])

def test_popup_view():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)

    table.view_mode = "popup"

    table.selections = [(slice(1, 2), slice(0, 2))]
    selection_equal(table.selections, [(slice(1, 2), slice(0, 2))])
    table.view_mode = "normal"

def test_color_mapper():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)

    @table.text_color.set("a")
    def _(val):
        return "red" if val < 2 else None

    @table.background_color.set("b")
    def _(val):
        return "green" if val < 20 else None

def test_set_scalar_via_cell_interface():
    viewer = TableViewer(show=False)
    table = viewer.add_table(np.zeros((6, 6)), editable=True)
    table.cell[2:4, 2:4] = 1
    assert np.all(table.data.iloc[2:4, 2:4].values == 1)
    table.cell[0, :] = 2
    assert np.all(table.data.iloc[0, :].values == 2)
    table.cell[:, 5] = 3
    assert np.all(table.data.iloc[:, 5].values == 3)

def test_set_list_via_cell_interface():
    viewer = TableViewer(show=False)
    table = viewer.add_table(np.zeros((6, 6)), editable=True)
    table.cell[2:4, 2:4] = [[1, 1], [1, 1]]
    assert np.all(table.data.iloc[2:4, 2:4].values == 1)
    table.cell[0, :] = [2] * 6
    assert np.all(table.data.iloc[0, :].values == 2)
    table.cell[:, 5] = [3] * 6
    assert np.all(table.data.iloc[:, 5].values == 3)

def test_header_interface():
    viewer = TableViewer(show=False)
    table = viewer.add_table(np.zeros((6, 6)), editable=True)

    assert table.index[0] == 0
    table.index[0] = "a"
    assert table.index[0] == "a"
    assert table.data.index[0] == "a"

    assert table.columns[0] == 0
    table.columns[0] = "x"
    assert table.columns[0] == "x"
    assert table.data.columns[0] == "x"


def test_cell_interface_in_spreadsheet():
    viewer = TableViewer(show=False)
    table = viewer.add_spreadsheet(np.zeros((6, 6)))
    assert table.data.shape == (6, 6)
    table.cell[0:8, 0] = np.arange(8)
    assert table.data.shape == (8, 6)
    assert np.all(table.data.iloc[0:8, 0].values == np.arange(8))

def test_cell_labels():
    viewer = TableViewer(show=False)
    table = viewer.add_spreadsheet(np.zeros((6, 6)))
    assert table.data.shape == (6, 6)
    table.cell.label[0, 0] = "a ="
    assert table.cell.label[0, 0] == "a ="
    table.undo_manager.undo()
    assert table.cell.label[0, 0] is None
    table.undo_manager.redo()
    assert table.cell.label[0, 0] == "a ="

def test_cell_labeled_data():
    viewer = TableViewer(show=False)
    table = viewer.add_spreadsheet(np.zeros((6, 6)))
    table.cell.set_labeled_data(0, 0, {"a:": 10, "b:": 20})
    assert table.cell.label[0, 0] == "a:"
    assert table.cell.label[1, 0] == "b:"
    assert table.cell[0, 0] == "10"
    assert table.cell[1, 0] == "20"
    table.undo_manager.undo()
    assert table.cell.label[0, 0] is None
    assert table.cell.label[1, 0] is None
    assert table.cell[0, 0] == "0.0"
    assert table.cell[1, 0] == "0.0"
    table.undo_manager.redo()
    assert table.cell.label[0, 0] == "a:"
    assert table.cell.label[1, 0] == "b:"
    assert table.cell[0, 0] == "10"
    assert table.cell[1, 0] == "20"


def test_side_area():
    viewer = TableViewer(show=False)
    table = viewer.add_spreadsheet(np.zeros((6, 6)))
    @magicgui
    def f(x: int):
        pass

    table.add_side_widget(f)

    line = QtW.QLineEdit()
    table.add_side_widget(line)

def test_overlay_widget():
    viewer = TableViewer(show=False)
    table = viewer.add_spreadsheet(np.zeros((6, 6)))
    @magicgui
    def f(x: int):
        pass

    table.add_overlay_widget(f)

    line = QtW.QLineEdit()
    table.add_overlay_widget(line)
