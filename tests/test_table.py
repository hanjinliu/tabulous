from tabulous import Table, TableViewer
from unittest.mock import MagicMock
import pandas as pd
import numpy as np
import pytest

df0 = pd.DataFrame({"a": [10, 20, 30], "b": [1.0, 1.1, 1.2]})
df1 = pd.DataFrame({"label": ["one", "two", "one"], "value": [1.0, 1.1, 1.2]})

def get_cell_value(table, row, col):
    index = table.model().index(row, col)
    return table.model().data(index)

def edit_cell(table, row, col, value):
    table.model().dataEdited.emit(row, col, value)

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

@pytest.mark.parametrize("df", [df0, df1])
def test_editing_data(df: pd.DataFrame):
    viewer = TableViewer(show=False)
    table = viewer.add_table(np.zeros((3, 3)))
    table.data = df
    assert str(table.data.iloc[0, 0]) == str(df.iloc[0, 0])

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
    mock.assert_called_with(sel)
