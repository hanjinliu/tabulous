from tabulous import TableViewer
import pandas as pd
from pandas.testing import assert_frame_equal

# group by single column
df0 = pd.DataFrame({
    "a": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    "b": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    "c": ["A", "B", "A", "A", "B", "A", "A", "B", "A", "B"],
})

# group by two columns
df1 = pd.DataFrame({
    "a": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    "b": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    "c": ["A", "B", "A", "A", "B", "A", "A", "B", "A", "B"],
    "d": ["X", "X", "Y", "Y", "X", "X", "Y", "Y", "Y", "Y"],
})

def test_add_groupby_single():
    viewer = TableViewer(show=False)
    grouped = df0.groupby("c")
    table = viewer.add_groupby(grouped, name="test")
    each_df = [x[1] for x in grouped]
    assert table.group == "A"
    assert_frame_equal(each_df[0], table._qwidget.model().df)
    table.group = "B"
    assert table.group == "B"
    assert_frame_equal(each_df[1], table._qwidget.model().df)

def test_add_groupby_double():
    viewer = TableViewer(show=False)
    table = viewer.add_groupby(df1.groupby(["c", "d"]))
