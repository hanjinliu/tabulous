from datetime import datetime as dt, timedelta as td
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
def test_display(df: pd.DataFrame, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = Table(df)
    viewer.add_layer(table)
    assert table.data is df
    assert table.data.columns is df.columns
    assert table.data.index is df.index
    assert table.table_shape == df.shape
    assert table.cell.text[0, 0] == str(df.iloc[0, 0])

@pytest.mark.parametrize("df", [df0, df1])
def test_editing_data(df: pd.DataFrame, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = Table(df)
    viewer.add_layer(table)
    edit_cell(table._qwidget, 0, 0, "11")
    assert str(df.iloc[0, 0]) == "11"

@pytest.mark.parametrize(
    "data, works, errors",
    [(pd.interval_range(0, periods=3, freq=2), "(1, 2]", "(2,]"),
     (pd.date_range("2020-01-01", periods=3, freq="3d"), "2020-01-02 00:00:00", "xyz"),
     (pd.timedelta_range("00:00:00", periods=3, freq="10s"), "0 days 00:00:10", "xyz"),
     (pd.period_range("2020-01-01", periods=3, freq="3d"), "2020-01-04", "xyz"),]
)
def test_editing_object_type(data, works: str, errors: str, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    df = {"a": data}
    works, errors = str(works), str(errors)
    table = viewer.add_table(df, editable=True)
    edit_cell(table._qwidget, 0, 0, works)
    assert table.cell.text[0, 0] == works
    with pytest.raises(Exception):
        table.cell[0, 0] = errors
    assert table.cell.text[0, 0] == works

@pytest.mark.parametrize(
    "data, works, errors",
    [(["a", "b", "a"], "b", "c"),
     ([0, 1, 0], 1, 2),
     ([0.0, 1.0, 0.0], "1.0", "2.0"),
     ([pd.Interval(0, 1), pd.Interval(1, 2), pd.Interval(0, 1)], "(1, 2]", "(2, 3]"),
     ([dt(2020, 1, 1), dt(2020, 1, 2), dt(2020, 1, 1)], dt(2020, 1, 2), dt(2020, 1, 3)),
     ([td(0), td(1), td(0)], "1 days 00:00:00", "2 days 00:00:00"),
     ]
)
def test_edit_category_type(data, works: str, errors: str, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    df = {"a": pd.Series(data, dtype="category")}
    works, errors = str(works), str(errors)
    table = viewer.add_table(df, editable=True)
    edit_cell(table._qwidget, 0, 0, works)
    assert table.cell.text[0, 0] == works
    with pytest.raises(Exception):
        table.cell[0, 0] = errors
    assert table.cell.text[0, 0] == works


def test_copy(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    df = pd.DataFrame({"a": [1, 2, 3], "b": [0, 0, 0]})
    table = viewer.add_table(df, copy=True, editable=True)
    table.cell[0, 0] = "11"
    assert df.iloc[0, 0] == 1

    df = pd.DataFrame({"a": [1, 2, 3], "b": [0, 0, 0]})
    table = viewer.add_table(df, copy=False, editable=True)
    table.cell[0, 0] = "11"
    assert df.iloc[0, 0] == 11

def test_cell_interface(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    df = pd.DataFrame({"a": [1, 2, 3], "b": [0, 0, 0]})
    table = viewer.add_table(df, copy=True, editable=True)

    mock = MagicMock()
    table.events.data.connect(mock)
    mock.assert_not_called()
    table.cell[0, 0] = "11"
    mock.assert_called_once()

@pytest.mark.parametrize("df", [df0, df1])
def test_updating_data(df: pd.DataFrame, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table(np.zeros((3, 3)))
    table.data = df
    assert str(table.data.iloc[0, 0]) == str(df.iloc[0, 0])

@pytest.mark.parametrize("df", [df0, df1])
def test_editing_original_data(df: pd.DataFrame, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    df = df.copy()
    table = viewer.add_table(df, copy=False, editable=True)
    table.data.iloc[0, 1] = -1.
    table.cell[1, 1] = "100.0"
    assert df.iloc[0, 1] == -1.
    assert df.iloc[1, 1] == 100.


def test_size_change(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = Table(np.zeros((30, 30)))
    viewer.add_layer(table)

    table.data = np.zeros((20, 20))
    assert table.table_shape == (20, 20)
    table.data = np.zeros((40, 40))
    assert table.table_shape == (40, 40)


def test_move_location(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table(df0)

    table.move_loc(1, "a")
    table.move_iloc(2, 1)

    with pytest.raises(IndexError):
        table.move_iloc(2, 5)

    with pytest.raises(IndexError):
        table.move_iloc(5, 2)

def test_assign(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table(df0)
    table.assign(c=[1, 2, 3])
    assert all(table.columns == ["a", "b", "c"])
    assert all(table.data["c"] == [1, 2, 3])

    table.assign(b=[True, False, True])
    assert all(table.columns == ["a", "b", "c"])
    assert all(table.data["b"] == [True, False, True])
    assert table.data.dtypes[1] == bool

def test_dual_view(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table(df0)

    table.view_mode = "horizontal"
    table.view_mode = "vertical"
    table.view_mode = "normal"
    table.view_mode = "vertical"
    table.view_mode = "horizontal"

    table.selections = [(slice(1, 2), slice(0, 2))]
    selection_equal(table.selections, [(slice(1, 2), slice(0, 2))])

def test_popup_view(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table(df0)

    table.view_mode = "popup"

    table.selections = [(slice(1, 2), slice(0, 2))]
    selection_equal(table.selections, [(slice(1, 2), slice(0, 2))])
    table.view_mode = "normal"

def test_color_mapper(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table(df0)

    @table.text_color.set("a")
    def _(val):
        return "red" if val < 2 else None

    @table.background_color.set("b")
    def _(val):
        return "green" if val < 20 else None

def test_set_scalar_via_cell_interface(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table(np.zeros((6, 6)), editable=True)
    table.cell[2:4, 2:4] = 1
    assert np.all(table.data.iloc[2:4, 2:4].values == 1)
    table.cell[0, :] = 2
    assert np.all(table.data.iloc[0, :].values == 2)
    table.cell[:, 5] = 3
    assert np.all(table.data.iloc[:, 5].values == 3)

def test_set_list_via_cell_interface(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table(np.zeros((6, 6)), editable=True)
    table.cell[2:4, 2:4] = [[1, 1], [1, 1]]
    assert np.all(table.data.iloc[2:4, 2:4].values == 1)
    table.cell[0, :] = [2] * 6
    assert np.all(table.data.iloc[0, :].values == 2)
    table.cell[:, 5] = [3] * 6
    assert np.all(table.data.iloc[:, 5].values == 3)

def test_header_interface(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table(np.zeros((6, 6)), editable=True)

    assert table.index[0] == 0
    table.index[0] = "a"
    assert table.index[0] == "a"
    assert table.data.index[0] == "a"

    assert table.columns[0] == 0
    table.columns[0] = "x"
    assert table.columns[0] == "x"
    assert table.data.columns[0] == "x"


def test_cell_interface_in_spreadsheet(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet(np.zeros((6, 6)))
    assert table.data.shape == (6, 6)
    table.cell[0:8, 0] = np.arange(8)
    assert table.data.shape == (8, 6)
    assert np.all(table.data.iloc[0:8, 0].values == np.arange(8))

def test_cell_labels(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet(np.zeros((6, 6)))
    assert table.data.shape == (6, 6)
    table.cell.label[0, 0] = "a ="
    assert table.cell.label[0, 0] == "a ="
    table.undo_manager.undo()
    assert table.cell.label[0, 0] is None
    table.undo_manager.redo()
    assert table.cell.label[0, 0] == "a ="

def test_cell_labeled_data(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
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


def test_side_area(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet(np.zeros((6, 6)))
    @magicgui
    def f(x: int):
        pass

    table.add_side_widget(f)

    line = QtW.QLineEdit()
    table.add_side_widget(line)

def test_overlay_widget(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_spreadsheet(np.zeros((6, 6)))
    @magicgui
    def f(x: int):
        pass

    table.add_overlay_widget(f)

    line = QtW.QLineEdit()
    table.add_overlay_widget(line)
