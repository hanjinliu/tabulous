# from tabulous import MagicTableViewer
# from tabulous.widgets import MagicTable
# from magicgui.widgets import Container

# def test_properties():
#     viewer = MagicTableViewer(name="test", label="label", tooltip="tooltip", visible=True, enabled=False)
#     assert viewer.visible
#     viewer.visible = False
#     assert not viewer.enabled
#     viewer.enabled = False
#     assert viewer.name == "test"
#     viewer.name = "test2"
#     assert viewer.label == "label"
#     assert viewer.tooltip == "tooltip"

# def test_containers():
#     ctn = Container()
#     viewer0 = MagicTableViewer(tab_position="top")
#     viewer1 = MagicTableViewer(tab_position="left")
#     ctn.append(viewer0)
#     ctn.append(viewer1)

# def test_table():
#     ctn = Container()
#     table0 = MagicTable({"a": [1, 2, 3]}, name="table_0")
#     table1 = MagicTable({"b": [3, 2, 1]}, name="table_1")
#     ctn.append(table0)
#     ctn.append(table1)
