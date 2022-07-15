from tabulous import MagicTableViewer
from magicgui.widgets import Container

def test_properties():
    viewer = MagicTableViewer(name="test", label="label", tooltip="tooltip", visible=True, enabled=False)
    assert viewer.visible
    viewer.visible = False
    assert not viewer.enabled
    viewer.enabled = False
    assert viewer.name == "test"
    viewer.name = "test2"
    assert viewer.label == "label"
    assert viewer.tooltip == "tooltip"    

def test_containers():
    ctn = Container()
    viewer0 = MagicTableViewer(tab_position="top")
    viewer1 = MagicTableViewer(tab_position="left")
    ctn.append(viewer0)
    ctn.append(viewer1)
