from tabulous import TableLayer, TableViewer

import pandas as pd
import numpy as np
import pytest

df0 = pd.DataFrame({"a": [10, 20, 30], "b": [1.0, 1.1, 1.2]})
df1 = pd.DataFrame({"label": ["one", "two", "one"], "value": [1.0, 1.1, 1.2]})

@pytest.mark.parametrize("df", [df0, df1])
def test_display(df: pd.DataFrame):
    viewer = TableViewer(show=False)
    table = TableLayer(df)
    viewer.add_layer(table)
    table.refresh()
    assert table.data is df
    assert table.columns is df.columns
    assert table.index is df.index
    assert table.shape == df.shape
    assert table._qwidget.item(0, 0).text() == str(df.iloc[0, 0])

@pytest.mark.parametrize("df", [df0, df1])
def test_update(df: pd.DataFrame):
    viewer = TableViewer(show=False)
    table = TableLayer(df)
    viewer.add_layer(table)
    table.refresh()
    table._qwidget.item(0, 0).setText("11")
    table._qwidget.itemDelegate().edited.emit((0, 0))
    assert str(df.iloc[0, 0]) == "11"

def test_size_change():
    viewer = TableViewer(show=False)
    table = TableLayer(np.zeros((30, 30)))
    viewer.add_layer(table)
    table.refresh()
    
    table.data = np.zeros((20, 20))
    assert table.shape == (20, 20)
    table.data = np.zeros((40, 40))
    assert table.shape == (40, 40)
