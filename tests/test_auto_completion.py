from tabulous import TableViewer

def test_table_list_completion(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    viewer.add_table({}, name="A0")
    viewer.add_table({}, name="B0")
    viewer.add_table({}, name="X")
    assert viewer.tables._ipython_key_completions_() == ["A0", "B0", "X"]

def test_table_completion(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table({"x": [1, 2], "yy": [4, 3]})
    assert table._ipython_key_completions_() == ["x", "yy"]

def test_table_subset_completion(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    table = viewer.add_table({"x": [1, 2], "y": [4, 3], "z": [0, 0]})
    sub = table.iloc[:, 1:]
    assert sub._ipython_key_completions_() == ["y", "z"]
