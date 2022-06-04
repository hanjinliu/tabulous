from magicgui import magicgui
from tabulous import TableViewer
from magicgui.widgets import PushButton

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
    
    assert len(f["df"].choices) == 0
    
    viewer.add_table({"a": [0, 0], "b": [1, 1]}, name="table-0")
    
    assert len(f["df"].choices) == 1
    value = f["df"].value 
    assert all(value["a"] == [0, 0])
    assert all(value["b"] == [1, 1])
    
    viewer.add_table({"a": [0, 0], "b": [1, 1]}, name="table-1")
    assert len(f["df"].choices) == 2
    viewer.tables.pop()
    assert len(f["df"].choices) == 1
    viewer.tables.pop()
    assert len(f["df"].choices) == 0
    

def test_table_column_choice():
    from tabulous.types import TableColumn
    viewer = TableViewer(show=False)
    
    @magicgui
    def f(df: TableColumn):
        pass
    
    viewer.add_dock_widget(f)
    
    assert f["df"].choices == ()
    
    viewer.add_table({"a": [0, 0], "b": [1, 1]}, name="table-0")
    
    assert len(f["df"]._dataframe_choices.choices) == 1
    assert len(f["df"]._column_choices.choices) == 2
    value = f["df"].value
    assert all(value == [0, 0])

    viewer.add_table({"a": [0, 0, 1]}, name="table-1")
    assert len(f["df"]._dataframe_choices.choices) == 2
    assert len(f["df"]._column_choices.choices) == 2
    
    f["df"]._dataframe_choices.value = "table-1"
    
    assert len(f["df"]._column_choices.choices) == 1
    assert all(value == [0, 0, 1])
