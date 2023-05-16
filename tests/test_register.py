from tabulous import TableViewer, TableViewerWidget, MagicTableViewer
from tabulous.widgets import TableViewerBase
import pytest
from pytestqt.qtbot import QtBot
from qtpy.QtCore import Qt
from unittest.mock import MagicMock

@pytest.mark.parametrize("cls", [TableViewer, TableViewerWidget, MagicTableViewer])
def test_register_table_keymap(qtbot: QtBot, cls: "type[TableViewerBase]"):
    viewer = cls(show=False)
    mock = MagicMock()

    qtbot.addWidget(viewer._qwidget)
    sheet = viewer.add_spreadsheet()
    @sheet.keymap.register("Ctrl+U")
    def test_func():
        mock()

    mock.assert_not_called()
    qtbot.keyClick(sheet._qwidget, "U", Qt.KeyboardModifier.ControlModifier)
    mock.assert_called_once()

    mock.reset_mock()
    sheet.keymap.unregister("Ctrl+U")
    mock.assert_not_called()

@pytest.mark.parametrize("cls", [TableViewer, TableViewerWidget, MagicTableViewer])
def test_register_viewer_keymap(qtbot: QtBot, cls: "type[TableViewerBase]"):
    viewer = cls(show=False)
    mock = MagicMock()

    qtbot.addWidget(viewer._qwidget)

    @viewer.keymap.register("Ctrl+U")
    def test_func():
        mock()

    mock.assert_not_called()
    qtbot.keyClick(viewer._qwidget, "U", Qt.KeyboardModifier.ControlModifier)
    mock.assert_called_once()

    mock.reset_mock()
    viewer.keymap.unregister("Ctrl+U")
    mock.assert_not_called()
    viewer.close()

@pytest.mark.parametrize("attr", ["cell", "index", "columns"])
def test_register_actions(attr: str, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet()
    name = "TEST"

    assert name not in getattr(sheet, attr)._qcontextmenu._actions
    getattr(sheet, attr).register(name, lambda: None)
    assert name in getattr(sheet, attr)._qcontextmenu._actions
