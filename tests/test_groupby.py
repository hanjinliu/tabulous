from tabulous import TableViewerWidget
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
    viewer = TableViewerWidget(show=False)
    grouped = df0.groupby("c")
    table = viewer.add_groupby(grouped, name="test")
    each_df = [x[1] for x in grouped]
    assert table.current_group == "A"
    assert_frame_equal(each_df[0], table._qwidget.dataShown())
    table.current_group = "B"
    assert table.current_group == "B"
    assert_frame_equal(each_df[1], table._qwidget.dataShown())

def test_add_groupby_double():
    viewer = TableViewerWidget(show=False)
    table = viewer.add_groupby(df1.groupby(["c", "d"]))
    assert table.current_group == ("A", "X")

def test_add_list():
    viewer = TableViewerWidget(show=False)
    table = viewer.add_groupby(
        [{"C0": [0, 0], "C1": [1, 1]},
         {"C0": [5, 0], "C1": [6, 1]},]
    )
    assert table.current_group == 0

def test_add_dict():
    viewer = TableViewerWidget(show=False)
    table = viewer.add_groupby(
        {"a": {"C0": [0, 0], "C1": [1, 1]},
         "b": {"C0": [5, 0], "C1": [6, 1]},}
    )
    assert table.current_group == "a"
