import numpy as np
from tabulous import TableViewer
import pandas as pd
from numpy.testing import assert_allclose
import pytest

def test_scalar():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet(pd.DataFrame({"a": [1, 3, 5]}))
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("&=np.mean(df['a'][0:3])", (0, 1))
    assert qtable._focused_widget is not None
    editor.eval_and_close()
    assert (0, 1) in list(qtable._ref_graphs.keys())
    assert qtable._focused_widget is None
    assert sheet.data.iloc[0, 1] == 3.0

    # changing data triggers re-evaluation
    sheet.cell[0, 0] = 4
    assert sheet.data.iloc[0, 1] == 4.0
    sheet.cell[0, 0] = 7
    assert sheet.data.iloc[0, 1] == 5.0

def test_delete_ref_by_editing_the_cells():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet(pd.DataFrame({"a": [1, 3, 5]}))
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("&=np.mean(df['a'][0:3])", (0, 1))
    editor.eval_and_close()

    assert (0, 1) in list(qtable._ref_graphs.keys())
    sheet.cell[0, 2] = "10"
    assert (0, 1) in list(qtable._ref_graphs.keys())
    sheet.cell[0, 1] = "10"
    assert (0, 1) not in list(qtable._ref_graphs.keys())

def test_delete_ref_by_editing_many_cells():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet(pd.DataFrame({"a": [1, 3, 5]}))
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("&=np.mean(df['a'][0:3])", (0, 1))
    editor.eval_and_close()

    assert (0, 1) in list(qtable._ref_graphs.keys())
    sheet.cell[0:2, 2] = "10"
    assert (0, 1) in list(qtable._ref_graphs.keys())
    sheet.cell[0:3, 1] = ["10", "10", "20"]
    assert (0, 1) not in list(qtable._ref_graphs.keys())

def test_eval_with_no_ref():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet()
    sheet.cell[0, 0] = "&=np.arange(5)"
    assert len(sheet.cellref) == 0

def test_1x1_ref_overwritten_by_Nx1_eval():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 2, 3]})
    sheet.cell[0, 1] = "&=np.mean(df['a'][0:3])"
    assert (0, 1) in sheet.cellref
    sheet.cell[1, 1] = "&=np.cumsum(df['a'][0:3])"
    assert (0, 1) not in sheet.cellref
    assert (1, 1) in sheet.cellref

def test_eval_undo():
    viewer = TableViewer(show=False)
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

def test_eval_undo_with_many_cells():
    viewer = TableViewer(show=False)
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

def test_eval_undo_with_overwrite():
    import numpy as np
    viewer = TableViewer(show=False)
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
def test_many_expr(expr: str):
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet(
        {"a": [1, 2, 3, 4, 5], "b": [5, 4, 3, 4, 5]}
    )
    sheet.cell[1, 2] = f"&={expr}"
    assert_allclose(sheet.data.iloc[:, 2].values, eval(expr, {"df": sheet.data, "np": np}, {}))

def test_returns_shorter():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet(
        {"a": [1, 2, 3, 4, 5], "b": [5, 4, 3, 4, 5]}
    )
    sheet.cell[1, 2] = f"&=np.diff(df['a'][:])"
    assert_allclose(sheet.data.iloc[:, 2].values, [1, 1, 1, 1, np.nan])

def test_called_once():
    viewer = TableViewer(show=False)
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

# def test_ref_after_insert():
#     ...

# def test_ref_after_removal():
#     ...
