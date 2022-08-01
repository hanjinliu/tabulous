from magicgui import magicgui
from tabulous import TableViewer
from magicgui.widgets import PushButton

def dataframe_equal(a, b):
    """Check two DataFrame (or tuple of DataFrames) are equal."""
    if isinstance(a, tuple):
        if a == ():
            return a == b
        return all(dataframe_equal(a0, b0) for a0, b0 in zip(a, b))
    return a.equals(b)

def test_add_and_remove():
    viewer = TableViewer(show=False)
    name = "NAME"
    btn = PushButton(text="test_button", name=name)
    dock = viewer.add_dock_widget(btn)
    assert dock.windowTitle() == name
    assert name in list(viewer._dock_widgets.keys())
    viewer.remove_dock_widget(name)
    assert name not in list(viewer._dock_widgets.keys())

def test_table_choice():
    from tabulous.types import TableData
    viewer = TableViewer(show=False)

    @magicgui
    def f(df: TableData):
        pass

    viewer.add_dock_widget(f)

    assert f["df"].choices == ()

    table0 = viewer.add_table({"a": [0, 0], "b": [1, 1]}, name="table-0")

    assert dataframe_equal(f["df"].choices, (table0.data,))
    value = f["df"].value
    assert all(value["a"] == [0, 0])
    assert all(value["b"] == [1, 1])

    table1 = viewer.add_table({"a": [0, 0], "b": [1, 1]}, name="table-1")
    assert dataframe_equal(f["df"].choices, (table0.data, table1.data))
    viewer.tables.pop()
    assert dataframe_equal(f["df"].choices, (table0.data,))
    viewer.tables.pop()
    assert dataframe_equal(f["df"].choices, ())

def test_layer_update():
    from tabulous.types import TableData
    viewer = TableViewer(show=False)

    @magicgui
    def f(df: TableData) -> TableData:
        return df

    viewer.add_dock_widget(f)

    table0 = viewer.add_table({"a": [0, 0], "b": [1, 1]}, name="table-0")

    f.call_button.clicked()
    assert len(viewer.tables) == 2
    result = viewer.tables[-1]
    assert dataframe_equal(result.data, table0.data)

    # second click will not add a new layer
    f.call_button.clicked()
    assert len(viewer.tables) == 2

def test_table_column_choice():
    from tabulous.types import TableColumn
    viewer = TableViewer(show=False)

    @magicgui
    def f(df: TableColumn):
        pass

    viewer.add_dock_widget(f)

    assert f["df"]._dataframe_choices.choices == ()
    assert f["df"]._column_choices.choices == ()

    table0 = viewer.add_table({"a": [0, 0], "b": [1, 1]}, name="table-0")

    assert len(f["df"]._dataframe_choices.choices) == 1
    assert len(f["df"]._column_choices.choices) == 2
    assert all(f["df"].value == [0, 0])

    table1 = viewer.add_table({"a": [0, 0, 1]}, name="table-1")
    assert len(f["df"]._dataframe_choices.choices) == 2
    assert len(f["df"]._column_choices.choices) == 2

    assert dataframe_equal(f["df"]._dataframe_choices.value, table0.data)

    del viewer.tables["table-0"]

    assert len(f["df"]._column_choices.choices) == 1
    assert all(f["df"].value == [0, 0, 1])
