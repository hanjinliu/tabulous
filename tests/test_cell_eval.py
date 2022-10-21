from tabulous import TableViewer

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

def test_vectorized_calculation():
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
