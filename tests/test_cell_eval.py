from tabulous import TableViewer
import pandas as pd
import pytest

def test_set_ndarray():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet()
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("=np.arange(10)", (0, 0))
    assert qtable._focused_widget is not None
    editor.eval_and_close()
    assert qtable._focused_widget is None
    for i in range(10):
        assert sheet.data.iloc[i, 0] == i

def test_column_vector_output():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 3, 5]})
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("=np.cumsum(df['a'][0:3])", (2, 1))
    editor.eval_and_close()
    assert sheet.data.iloc[0, 1] == 1
    assert sheet.data.iloc[1, 1] == 4
    assert sheet.data.iloc[2, 1] == 9

    # check evaluation at an existing column works
    editor = qtable._create_eval_editor("=np.cumsum(df['a'][0:3])", (1, 1))
    editor.eval_and_close()
    assert sheet.data.iloc[0, 1] == 1
    assert sheet.data.iloc[1, 1] == 4
    assert sheet.data.iloc[2, 1] == 9

def test_partial_column_vector_output():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 3, 5, 7]})
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("=np.cumsum(df['a'][1:3])", (2, 1))
    editor.eval_and_close()
    assert pd.isna(sheet.data.iloc[0, 1])
    assert sheet.data.iloc[1, 1] == 3
    assert sheet.data.iloc[2, 1] == 8
    assert pd.isna(sheet.data.iloc[3, 1])

    # check evaluation at an existing column works
    editor = qtable._create_eval_editor("=np.cumsum(df['a'][1:3])", (1, 1))
    editor.eval_and_close()
    assert pd.isna(sheet.data.iloc[0, 1])
    assert sheet.data.iloc[1, 1] == 3
    assert sheet.data.iloc[2, 1] == 8
    assert pd.isna(sheet.data.iloc[3, 1])

def test_row_vector_output():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 3, 5], "b": [2, 4, 6]})
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("=np.mean(df.loc[0:2, 'a':'b'], axis=0)", (4, 1))
    editor.eval_and_close()
    assert sheet.data.iloc[4, 0] == 3.0
    assert sheet.data.iloc[4, 1] == 4.0

    # check evaluation at an existing column works
    editor = qtable._create_eval_editor("=np.mean(df.loc[0:2, 'a':'b'], axis=0)", (4, 0))
    editor.eval_and_close()
    assert sheet.data.iloc[4, 0] == 3.0
    assert sheet.data.iloc[4, 1] == 4.0

def test_partial_row_vector_output():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 3, 5], "b": [2, 4, 6], "c": [7, 8, 9]})
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("=np.mean(df.loc[0:2, 'a':'b'], axis=0)", (4, 1))
    editor.eval_and_close()
    assert sheet.data.iloc[4, 0] == 3.0
    assert sheet.data.iloc[4, 1] == 4.0
    assert pd.isna(sheet.data.iloc[4, 2])

    # check evaluation at an existing column works
    editor = qtable._create_eval_editor("=np.mean(df.loc[0:2, 'a':'b'], axis=0)", (4, 0))
    editor.eval_and_close()
    assert sheet.data.iloc[4, 0] == 3.0
    assert sheet.data.iloc[4, 1] == 4.0
    assert pd.isna(sheet.data.iloc[4, 2])

def test_scalar_output():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 3, 5]})
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("=np.mean(df['a'][0:3])", (2, 1))
    editor.eval_and_close()
    assert sheet.data.iloc[2, 1] == 3.0

    # check evaluation at an existing column works
    editor = qtable._create_eval_editor("=np.mean(df['a'][0:3]) + 1", (1, 1))
    editor.eval_and_close()
    assert sheet.data.iloc[1, 1] == 4.0

def test_updating_namespace():
    import numpy as np
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"a": [1, 3, 5]})
    qtable = sheet.native._qtable_view
    with pytest.raises(ValueError):
        viewer.cell_namespace.update(np=0)
    viewer.cell_namespace.update(mean=np.mean)
    editor = qtable._create_eval_editor("=mean(df['a'][0:3])", (2, 1))
    editor.eval_and_close()
    assert sheet.data.iloc[2, 1] == 3.0
