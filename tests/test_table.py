from tabulous import Table, TableViewer
from unittest.mock import MagicMock
import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np
import pytest

df0 = pd.DataFrame({"a": [10, 20, 30], "b": [1.0, 1.1, 1.2]})
df1 = pd.DataFrame({"label": ["one", "two", "one"], "value": [1.0, 1.1, 1.2]})

def get_cell_value(table, row, col):
    index = table.model().index(row, col)
    return table.model().data(index)

def edit_cell(table, row, col, value):
    table.model().dataEdited.emit(row, col, value)

def slice_equal(s1: tuple[slice, slice], s2: tuple[slice, slice]):
    return (
        s1[0].start == s2[0].start and
        s1[1].start == s2[1].start and
        s1[0].stop == s2[0].stop and
        s1[1].stop == s2[1].stop
    )

def selection_equal(sel1: list[tuple[slice, slice]], sel2: list[tuple[slice, slice]]):
    if len(sel1) != len(sel2):
        return False
    for s1, s2 in zip(sel1, sel2):
        if not slice_equal(s1, s2):
            return False
    return True


@pytest.mark.parametrize("df", [df0, df1])
def test_display(df: pd.DataFrame):
    viewer = TableViewer(show=False)
    table = Table(df)
    viewer.add_layer(table)
    assert table.data is df
    assert table.data.columns is df.columns
    assert table.data.index is df.index
    assert table.table_shape == df.shape
    assert get_cell_value(table._qwidget, 0, 0) == str(df.iloc[0, 0])

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

def test_selection():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)

    table.selections = [(0, 0), (slice(1, 3), slice(1, 2))]

    sl0 = (slice(0, 1), slice(0, 1))
    sl1 = (slice(1, 3), slice(1, 2))
    assert selection_equal(table.selections, [sl0, (slice(1, 3), slice(1, 2))])
    assert slice_equal(table.selections[0], sl0)
    assert slice_equal(table.selections[1], sl1)
    assert_frame_equal(table.selections.values[0], table.data.iloc[sl0])
    assert_frame_equal(table.selections.values[1], table.data.iloc[sl1])


def test_size_change():
    viewer = TableViewer(show=False)
    table = Table(np.zeros((30, 30)))
    viewer.add_layer(table)

    table.data = np.zeros((20, 20))
    assert table.table_shape == (20, 20)
    table.data = np.zeros((40, 40))
    assert table.table_shape == (40, 40)

def test_selection_signal():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)
    mock = MagicMock()

    @table.events.selections.connect
    def f(sel):
        mock(sel)

    mock.assert_not_called()
    sel = [(slice(1, 2), slice(1, 2))]
    table.selections = sel
    mock.assert_called()

def test_move_location():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)

    table.move_loc(1, "a")
    table.move_iloc(2, 1)

    with pytest.raises(IndexError):
        table.move_iloc(2, 5)

    with pytest.raises(IndexError):
        table.move_iloc(5, 2)

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

def test_color_mapper():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)

    @table.foreground_colormap("a")
    def _(val):
        return "red" if val < 2 else None

    @table.background_colormap("b")
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
