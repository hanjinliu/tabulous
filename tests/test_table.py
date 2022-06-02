from tabulous import TableLayer
from tabulous._qt import get_app

import pandas as pd
import pytest

df0 = pd.DataFrame({"a": [1, 2, 3], "b": [1.0, 1.1, 1.2]})
df1 = pd.DataFrame({"label": ["one", "two", "one"], "value": [1.0, 1.1, 1.2]})
# app = get_app()

# @pytest.mark.parametrize("df", [df0, df1])
# def test_display(df: pd.DataFrame):
#     table = TableLayer(df)
#     assert table.data is df
#     assert table.columns is df.columns
#     assert table.index is df.index
#     assert table.shape == df.shape
#     assert table._qwidget.item(0, 0).text() == str(df0.iloc[0, 0])

# @pytest.mark.parametrize("df", [df0, df1])
# def test_update(df: pd.DataFrame):
#     table = TableLayer(df)
#     # table.show()
#     table._qwidget.item(0, 0).setText("11")
#     table._qwidget.itemDelegate().edited.emit((0, 0))
#     assert str(df.iloc[0, 0]) == "11"