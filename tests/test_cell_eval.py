from tabulous import TableViewer
import pandas as pd

def test_set_ndarray():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet()
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor(0, 0, "=np.arange(10)")
    assert qtable._overlay_editor is not None
    editor.eval_and_close()
    assert qtable._overlay_editor is None
    for i in range(10):
        assert sheet.data.iloc[i, 0] == i

def test_column_vector_output():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 3, 5]})
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor(2, 1, "=np.cumsum(df['a'][0:3])")
    editor.eval_and_close()
    assert sheet.data.iloc[0, 1] == 1
    assert sheet.data.iloc[1, 1] == 4
    assert sheet.data.iloc[2, 1] == 9

    # check evaluation at an existing column works
    editor = qtable._create_eval_editor(1, 1, "=np.cumsum(df['a'][0:3])")
    editor.eval_and_close()
    assert sheet.data.iloc[0, 1] == 1
    assert sheet.data.iloc[1, 1] == 4
    assert sheet.data.iloc[2, 1] == 9

def test_partial_column_vector_output():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 3, 5, 7]})
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor(2, 1, "=np.cumsum(df['a'][1:3])")
    editor.eval_and_close()
    assert pd.isna(sheet.data.iloc[0, 1])
    assert sheet.data.iloc[1, 1] == 3
    assert sheet.data.iloc[2, 1] == 8
    assert pd.isna(sheet.data.iloc[3, 1])

    # check evaluation at an existing column works
    editor = qtable._create_eval_editor(1, 1, "=np.cumsum(df['a'][1:3])")
    editor.eval_and_close()
    assert pd.isna(sheet.data.iloc[0, 1])
    assert sheet.data.iloc[1, 1] == 3
    assert sheet.data.iloc[2, 1] == 8
    assert pd.isna(sheet.data.iloc[3, 1])

def test_row_vector_output():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 3, 5], "b": [2, 4, 6]})
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor(4, 1, "=np.mean(df.loc[0:2, 'a':'b'], axis=0)")
    editor.eval_and_close()
    assert sheet.data.iloc[4, 0] == 3.0
    assert sheet.data.iloc[4, 1] == 4.0

    # check evaluation at an existing column works
    editor = qtable._create_eval_editor(4, 0, "=np.mean(df.loc[0:2, 'a':'b'], axis=0)")
    editor.eval_and_close()
    assert sheet.data.iloc[4, 0] == 3.0
    assert sheet.data.iloc[4, 1] == 4.0

def test_partial_row_vector_output():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 3, 5], "b": [2, 4, 6], "c": [7, 8, 9]})
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor(4, 1, "=np.mean(df.loc[0:2, 'a':'b'], axis=0)")
    editor.eval_and_close()
    assert sheet.data.iloc[4, 0] == 3.0
    assert sheet.data.iloc[4, 1] == 4.0
    assert pd.isna(sheet.data.iloc[4, 2])

    # check evaluation at an existing column works
    editor = qtable._create_eval_editor(4, 0, "=np.mean(df.loc[0:2, 'a':'b'], axis=0)")
    editor.eval_and_close()
    assert sheet.data.iloc[4, 0] == 3.0
    assert sheet.data.iloc[4, 1] == 4.0
    assert pd.isna(sheet.data.iloc[4, 2])

def test_scalar_output():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 3, 5]})
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor(2, 1, "=np.mean(df['a'][0:3])")
    editor.eval_and_close()
    assert sheet.data.iloc[2, 1] == 3.0

    # check evaluation at an existing column works
    editor = qtable._create_eval_editor(1, 1, "=np.mean(df['a'][0:3]) + 1")
    editor.eval_and_close()
    assert sheet.data.iloc[1, 1] == 4.0