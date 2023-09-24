import numpy as np
from tabulous import TableViewer
import pandas as pd
from numpy.testing import assert_allclose, assert_equal
import pytest

def test_scalar(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(pd.DataFrame({"a": [1, 3, 5]}))
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("&=np.mean(df['a'][0:3])", (0, 1))
    assert qtable._focused_widget is not None
    editor.eval_and_close()
    assert (0, 1) in list(qtable._table_map.keys())
    assert qtable._focused_widget is None
    assert sheet.data.iloc[0, 1] == 3.0

    # changing data triggers re-evaluation
    sheet.cell[0, 0] = 4
    assert sheet.data.iloc[0, 1] == 4.0
    sheet.cell[0, 0] = 7
    assert sheet.data.iloc[0, 1] == 5.0

def test_delete_ref_by_editing_the_cells(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(pd.DataFrame({"a": [1, 3, 5]}))
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("&=np.mean(df['a'][0:3])", (0, 1))
    editor.eval_and_close()

    assert (0, 1) in list(qtable._table_map.keys())
    sheet.cell[0, 2] = "10"
    assert (0, 1) in list(qtable._table_map.keys())
    sheet.cell[0, 1] = "10"
    assert (0, 1) not in list(qtable._table_map.keys())

def test_delete_ref_by_editing_many_cells(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(pd.DataFrame({"a": [1, 3, 5]}))
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("&=np.mean(df['a'][0:3])", (0, 1))
    editor.eval_and_close()

    assert (0, 1) in list(qtable._table_map.keys())
    sheet.cell[0:2, 2] = "10"
    assert (0, 1) in list(qtable._table_map.keys())
    sheet.cell[0:3, 1] = ["10", "10", "20"]
    assert (0, 1) not in list(qtable._table_map.keys())

def test_eval_with_no_ref(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet()
    sheet.cell[0, 0] = "&=np.arange(5)"
    assert len(sheet.cell.ref) == 0

def test_1x1_ref_overwritten_by_Nx1_eval(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet({"a": [1, 2, 3]})
    sheet.cell[0, 1] = "&=np.mean(df['a'][0:3])"
    assert (0, 1) in sheet.cell.ref
    sheet.cell[1, 1] = "&=np.cumsum(df['a'][0:3])"
    assert (0, 1) not in sheet.cell.ref
    assert (1, 1) in sheet.cell.ref

def test_eval_undo(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet({"a": [1, 2, 3]})
    sheet.cell[0, 1] = "&=np.mean(df['a'][0:3])"
    assert sheet.data.iloc[0, 1] == 2.0

    sheet.cell[0, 0] = "10"
    assert sheet.data.iloc[0, 1] == 5.0
    sheet.undo_manager.undo()
    assert sheet.data.iloc[0, 0] == 1
    assert sheet.data.iloc[0, 1] == 2.0
    sheet.undo_manager.redo()
    assert sheet.data.iloc[0, 0] == 10
    assert sheet.data.iloc[0, 1] == 5.0

def test_eval_undo_with_many_cells(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet({"a": [1, 2, 3]})
    sheet.cell[0, 1] = "&=np.cumsum(df['a'][0:3])"
    assert_allclose(sheet.data.iloc[:, 1].values, [1, 3, 6])

    sheet.cell[0, 0] = "10"
    assert_allclose(sheet.data.iloc[:, 1].values, [10, 12, 15])
    sheet.undo_manager.undo()
    assert sheet.data.iloc[0, 0] == 1
    assert_allclose(sheet.data.iloc[:, 1].values, [1, 3, 6])
    sheet.undo_manager.redo()
    assert sheet.data.iloc[0, 0] == 10
    assert_allclose(sheet.data.iloc[:, 1].values, [10, 12, 15])

def test_eval_undo_with_overwrite(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet({"a": [1, 2, 3]})
    sheet.cell[0, 1] = "&=np.mean(df['a'][0:3])"
    sheet.cell[1, 1] = "&=np.cumsum(df['a'][0:3])"
    assert_allclose(sheet.data.values, [[1, 1], [2, 3], [3, 6]])
    sheet.undo_manager.undo()
    assert_allclose(sheet.data.values, [[1, 2], [2, np.nan], [3, np.nan]])
    sheet.undo_manager.undo()
    assert_allclose(sheet.data.values, [[1], [2], [3]])

@pytest.mark.parametrize(
    "expr",
    [
        "df['a'][:]",
        "df['b'][:]",
        "df['a'][:] + df['b'][:]",
        "df['a'][:] + df['b'][:].mean()",
        "np.cumsum(df['a'][:])",  # function that returns a same-length array
        "np.mean(df.loc[:, 'a':'b'], axis=1)", # 1D reduction
        "df.loc[:, 'a':'b'].mean(axis=1)",  # 1D reduction
        "np.mean(df.loc[:, 'a':'b'], axis=1) + df['a'][:]",  # reduction + array
        "df['a'][:].values",  # array
    ]
)
def test_many_expr(expr: str, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(
        {"a": [1, 2, 3, 4, 5], "b": [5, 4, 3, 4, 5]}
    )
    sheet.cell[1, 2] = f"&={expr}"
    assert_allclose(sheet.data.iloc[:, 2].values, eval(expr, {"df": sheet.data, "np": np}, {}))

def test_returns_shorter(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(
        {"a": [1, 2, 3, 4, 5], "b": [5, 4, 3, 4, 5]}
    )
    sheet.cell[1, 2] = f"&=np.diff(df['a'][:])"
    assert_allclose(sheet.data.iloc[:, 2].values, [1, 1, 1, 1, np.nan])

def test_called_once(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    count = 0
    @viewer.cell_namespace.add
    def func(*_):
        nonlocal count
        count += 1
        return 0

    sheet = viewer.add_spreadsheet({"a": [1, 2, 3]})
    sheet.cell[0, 1] = "&=func(df['a'][:])"
    assert count == 1
    sheet.cell[0, 0] = "4"
    assert count == 2

def test_ref_after_insert(make_tabulous_viewer):
    # 0 0 0 0 0
    # 0 0 0 X 0 <- edit here
    # 0 0 0 0 0
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(np.zeros((3, 5), dtype=np.float32))
    sheet.cell[1, 3] = "&=np.sum(df.iloc[0:2, 0:1]) + 1"
    assert sheet.cell[1, 3] == "1.0"
    sheet.columns.insert(2, 1)  # insert a column
    assert sheet.cell[1, 3] == "0.0"
    assert sheet.cell[1, 4] == "1.0"
    assert (1, 3) not in sheet.cell.ref
    assert (1, 4) in sheet.cell.ref
    sheet.undo_manager.undo()
    assert sheet.cell[1, 3] == "1.0"
    assert sheet.cell[1, 4] == "0.0"
    assert (1, 3) in sheet.cell.ref
    assert (1, 4) not in sheet.cell.ref


def test_ref_after_removal(make_tabulous_viewer):
    # 0 0 0 0 0
    # 0 0 0 X 0 <- edit here
    # 0 0 0 0 0
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(np.zeros((3, 5), dtype=np.float32))
    sheet.cell[1, 3] = "&=np.sum(df.iloc[0:2, 0:1]) + 1"
    assert sheet.cell[1, 3] == "1.0"
    sheet.columns.remove(2, 1)  # insert a column
    assert sheet.cell[1, 3] == "0.0"
    assert sheet.cell[1, 2] == "1.0"
    assert (1, 3) not in sheet.cell.ref
    assert (1, 2) in sheet.cell.ref
    sheet.undo_manager.undo()
    assert sheet.cell[1, 3] == "1.0"
    assert sheet.cell[1, 2] == "0.0"
    assert (1, 3) in sheet.cell.ref
    assert (1, 2) not in sheet.cell.ref


def test_ref_after_removal_of_column(make_tabulous_viewer):
    # --- table ---
    # 0 0 0 0 0
    # 0 0 0 X 0  and delete the column including X
    # 0 0 0 0 0
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(np.zeros((3, 5), dtype=np.float32))
    sheet.cell[1, 3] = "&=np.sum(df.iloc[0:2, 0:1]) + 1"
    assert sheet.cell[1, 3] == "1.0"
    sheet.columns.remove(3, 1)  # remove a column
    assert sheet.cell[1, 3] == "0.0"
    assert len(sheet.cell.ref) == 0
    sheet.undo_manager.undo()
    assert sheet.cell[1, 3] == "1.0"
    assert sheet.cell[1, 2] == "0.0"
    assert (1, 3) in sheet.cell.ref
    assert (1, 2) not in sheet.cell.ref


def test_removing_source(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(np.zeros((3, 1), dtype=np.float32))
    sheet.cell[0, 1] = "&=np.sum(df.iloc[:, 0])"
    assert len(sheet.cell.ref) == 1
    sheet.columns.remove(0, 1)  # remove a column
    assert sheet.data.shape == (3, 1), "wrong shape"
    assert len(sheet.cell.ref) == 0, "slot not removed"


def test_removing_one_of_two_sources(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(np.zeros((3, 2), dtype=np.float32))
    sheet.cell[0, 2] = "&=np.sum(df.iloc[:, 0]) + np.sum(df.iloc[:, 1])"
    assert len(sheet.cell.ref) == 1
    sheet.columns.remove(0, 1)  # remove a column
    assert sheet.data.shape == (3, 2), "wrong shape"
    assert len(sheet.cell.ref) == 0, "slot not removed"

def test_removing_or_inserting_left_column(make_tabulous_viewer):
    # --- table ---
    # 0 0 &=np.sum(df.iloc[:, 1:2])
    # 0 0
    # 0 0
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet([[0., 1.], [1., 2.], [3., 5.]])
    sheet.cell[0, 2] = "&=np.sum(df.iloc[:, 1])"
    assert sheet.cell[0, 2] == "8.0"
    sheet.columns.remove(0, 1)  # remove a column
    assert sheet.data.shape == (3, 2)
    assert sheet.cell[0, 1] == "8.0"
    sheet.cell[1, 0] = 4
    assert sheet.cell[0, 1] == "10.0"
    sheet.columns.insert(0, 1)  # insert a column
    assert sheet.data.shape == (3, 3)
    assert sheet.cell[0, 2] == "10.0"
    sheet.cell[1, 0] = 5
    assert sheet.cell[0, 2] == "10.0"

def test_eval_during_sort(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    rng = np.random.default_rng(123)
    sheet = viewer.add_spreadsheet(rng.poisson(3, size=(5, 1)))
    sheet.proxy.set([1, 3, 2, 4, 0])
    sheet.cell[1, 1] = "&=np.sum(df.iloc[:, 0])"
    assert sheet.data_shown.iloc[1, 1] == np.sum(sheet.data.iloc[:, 0])
    sheet.proxy.reset()
    assert sheet.data_shown.iloc[3, 1] == np.sum(sheet.data.iloc[:, 0])
    assert (3, 1) in sheet.cell.ref

def test_eval_during_filter(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    rng = np.random.default_rng(123)
    sheet = viewer.add_spreadsheet({"a": [0, 1, 1, 0, 1], "b": rng.poisson(3, size=5)})
    sheet.proxy.filter("a == 1")
    sheet.cell[0, 2] = "&=np.sum(df.iloc[:, 1])"
    assert sheet.data_shown.iloc[0, 2] == np.sum(sheet.data.iloc[:, 1])
    sheet.proxy.reset()
    assert sheet.data_shown.iloc[1, 2] == np.sum(sheet.data.iloc[:, 1])
    assert (1, 2) in sheet.cell.ref

def test_broadcasting_during_sort(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    rng = np.random.default_rng(123)
    sheet = viewer.add_spreadsheet(rng.poisson(3, size=(5, 1)))
    order = [1, 3, 2, 4, 0]
    sheet.proxy.set(order)
    sheet.cell[1, 1] = "&=np.cumsum(df.iloc[:, 0])"
    assert_equal(sheet.data_shown.iloc[:, 1].values, np.cumsum(sheet.data.iloc[:, 0])[order].values)
    sheet.proxy.reset()
    assert_equal(sheet.data_shown.iloc[:, 1].values, np.cumsum(sheet.data.iloc[:, 0]).values)
    assert (3, 1) in sheet.cell.ref

def test_broadcasting_during_filter(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    rng = np.random.default_rng(123)
    sheet = viewer.add_spreadsheet({"a": [0, 1, 1, 0, 1], "b": rng.poisson(3, size=5)})
    sheet.proxy.filter("a == 1")
    idx = sheet.proxy.as_indexer()
    sheet.cell[0, 2] = "&=np.cumsum(df.iloc[:, 1])"
    assert_equal(sheet.data_shown.iloc[:, 2].values, np.cumsum(sheet.data.iloc[:, 1])[idx].values)
    sheet.proxy.reset()
    assert_equal(sheet.data_shown.iloc[:, 2].values, np.cumsum(sheet.data.iloc[:, 1]).values)
    assert (1, 2) in sheet.cell.ref

def _assert_status_equal(s: str, ref: str):
    l = len("<b><code>")
    r = len("</code></b>")
    assert s[l:-r] == ref

def test_status_tip(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(np.zeros((3, 2)))
    sheet.cell[0, 1] = "&=np.sum(df.iloc[:, 0])"
    sheet.cell[0, 2] = "&=np.sin(df.iloc[:, 0])"
    sheet.move_iloc(0, 0)
    _assert_status_equal(viewer.status, "")
    sheet.move_iloc(0, 1)
    _assert_status_equal(viewer.status, "df.iloc[0:1, 1:2] = np.sum(df.iloc[:, 0])")
    sheet.move_iloc(1, 1)
    _assert_status_equal(viewer.status, "")
    sheet.move_iloc(0, 2)
    _assert_status_equal(viewer.status, "df.iloc[:, 2:3] = np.sin(df.iloc[:, 0])")
    sheet.move_iloc(1, 2)
    _assert_status_equal(viewer.status, "df.iloc[:, 2:3] = np.sin(df.iloc[:, 0])")
    sheet.move_iloc(2, 2)
    _assert_status_equal(viewer.status, "df.iloc[:, 2:3] = np.sin(df.iloc[:, 0])")

def test_status_tip_with_proxy(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet(np.zeros((5, 2)))
    sheet.cell[1, 1] = "&=np.sum(df.iloc[:, 0])"
    sheet.cell[0, 2] = "&=np.sin(df.iloc[:, 0])"
    sheet.proxy.set([False, True, True, False, True])
    sheet.move_iloc(0, 0)
    _assert_status_equal(viewer.status, "")
    sheet.move_iloc(0, 1)
    _assert_status_equal(viewer.status, "df.iloc[1:2, 1:2] = np.sum(df.iloc[:, 0])")
    sheet.move_iloc(1, 1)
    _assert_status_equal(viewer.status, "")
    sheet.move_iloc(0, 2)
    _assert_status_equal(viewer.status, "df.iloc[:, 2:3] = np.sin(df.iloc[:, 0])")
    sheet.move_iloc(1, 2)
    _assert_status_equal(viewer.status, "df.iloc[:, 2:3] = np.sin(df.iloc[:, 0])")
    sheet.move_iloc(2, 2)
    _assert_status_equal(viewer.status, "df.iloc[:, 2:3] = np.sin(df.iloc[:, 0])")

def test_called_when_expanded(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    # check scalar output
    sheet = viewer.add_spreadsheet([[0, 1], [0, 2], [0, 3]])
    sheet.cell[1, 2] = "&=np.sum(df.iloc[:, 1])"
    assert sheet.data.iloc[1, 2] == 6
    sheet.cell[3, 1] = "4"
    assert sheet.data.iloc[1, 2] == 10

    # check vector output
    sheet = viewer.add_spreadsheet([[0, 1], [0, 2], [0, 3]])
    sheet.cell[1, 2] = "&=np.cumsum(df.iloc[:, 1])"
    assert_equal(sheet.data.iloc[:, 2].values, [1, 3, 6])
    sheet.cell[3, 1] = "4"
    assert_equal(sheet.data.iloc[:, 2].values, [1, 3, 6, 10])

def test_N(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet([[0, 1], [0, 2], [0, 3]])
    sheet.cell[1, 2] = "&=np.sum(df.iloc[:, 1])/N"
    assert sheet.data.iloc[1, 2] == 2
    sheet.cell[3, 1] = "4"
    assert sheet.data.iloc[1, 2] == 2.5
    sheet.cell[1, 3] = "&=np.zeros(N)"
    assert sheet.data.iloc[1, 3] == 0
