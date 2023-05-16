from __future__ import annotations

from unittest.mock import MagicMock
from tabulous import TableViewer, TableViewerWidget
import numpy as np
from ._utils import get_tabwidget_tab_name
import pytest

test_data = {"a": [1, 2, 3], "b": [4, 5, 6]}

@pytest.mark.parametrize("viewer_cls", [TableViewer, TableViewerWidget])
def test_add_layers(viewer_cls: type[TableViewerWidget]):
    viewer = viewer_cls(show=False)
    viewer.add_table(test_data, name="Data")
    df = viewer.tables[0].data
    assert viewer.current_index == 0
    agg = df.agg([np.mean, np.std])
    viewer.add_table(agg, name="Data")
    assert viewer.current_index == 1
    assert viewer.tables[0].name == "Data"
    assert viewer.tables[1].name == "Data-0"
    assert np.all(df == viewer.tables[0].data)
    assert np.all(agg == viewer.tables[1].data)
    viewer.close()

@pytest.mark.parametrize("viewer_cls", [TableViewer, TableViewerWidget])
@pytest.mark.parametrize("pos", ["top", "left"])
def test_renaming(viewer_cls: type[TableViewerWidget], pos):
    viewer = viewer_cls(tab_position=pos, show=False)
    table0 = viewer.add_table(test_data, name="Data")
    assert table0.name == "Data"
    assert get_tabwidget_tab_name(viewer, 0) == "Data"
    table0.name = "Data-0"
    assert table0.name == "Data-0"
    assert get_tabwidget_tab_name(viewer, 0) == "Data-0"
    table1 = viewer.add_table(test_data.copy(), name="Data-1")
    assert table0.name == "Data-0"
    assert table1.name == "Data-1"
    assert get_tabwidget_tab_name(viewer, 0) == "Data-0"
    assert get_tabwidget_tab_name(viewer, 1) == "Data-1"

    # name of newly added table will be renamed if there are collision.
    table2 = viewer.add_table(test_data.copy(), name="Data-0")
    assert table2.name == "Data-2"
    assert get_tabwidget_tab_name(viewer, 2) == "Data-2"

    # new name will be renamed if there are collision.
    table1.name = "Data-2"
    assert table1.name == "Data-3"
    assert get_tabwidget_tab_name(viewer, 1) == "Data-3"

    # no need for coercing if the table is already removed.
    name = viewer.tables[0].name
    del viewer.tables[0]
    table1.name = name
    assert table1.name == name
    assert get_tabwidget_tab_name(viewer, 0) == name

    viewer.close()

@pytest.mark.parametrize(
    "src, dst",
    [(0, 1), (1, 0), (0, 2), (2, 0)]
)
def test_move(src: int, dst: int, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    names = ["0", "1", "2"]
    for name in names:
        viewer.add_spreadsheet(name=name)
    viewer.tables.move(src, dst)
    assert [t.name for t in viewer.tables] == [viewer.native._tablestack.tabText(i) for i in range(3)]

@pytest.mark.parametrize("viewer_cls", [TableViewer, TableViewerWidget])
def test_register_action(viewer_cls: type[TableViewerWidget]):
    viewer = viewer_cls(show=False)
    @viewer.tables.register
    def f(viewer, i):
        pass

    @viewer.tables.register("register-test")
    def g(viewer, i):
        pass

    @viewer.tables.register("Tests > name")
    def h(viewrer, i):
        pass

    viewer.close()

@pytest.mark.parametrize("viewer_cls", [TableViewer, TableViewerWidget])
def test_components(viewer_cls: type[TableViewerWidget]):
    viewer = viewer_cls(show=True)

    assert not viewer.console.visible
    viewer.console.visible = True
    assert viewer.console.visible
    viewer.console.visible = False
    assert not viewer.console.visible

    viewer.toolbar.visible = True
    assert viewer.toolbar.visible
    viewer.toolbar.visible = False
    assert not viewer.toolbar.visible

    viewer.close()

@pytest.mark.parametrize("viewer_cls", [TableViewer, TableViewerWidget])
def test_bind_keycombo(viewer_cls: type[TableViewerWidget]):
    viewer = viewer_cls(show=False)

    mock = MagicMock()

    viewer.keymap.register("T")(mock)
    mock.assert_not_called()
    viewer.keymap.press_key("T")
    mock.assert_called_once()

    with pytest.raises(Exception):
        viewer.keymap.register("T")(mock)
    viewer.keymap.register("T", overwrite=True)(print)

    viewer.close()
