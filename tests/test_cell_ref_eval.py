from tabulous import TableViewer
import pandas as pd
from numpy.testing import assert_allclose

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
