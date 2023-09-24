import sys
import pytest
import numpy as np
from pytestqt.qtbot import QtBot
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

def test_add_spreadsheet_and_move(make_tabulous_viewer, qtbot: QtBot):
    viewer = make_tabulous_viewer()
    qtbot.addWidget(viewer._qwidget)
    qtbot.keyClick(viewer._qwidget, Qt.Key.Key_N, Qt.KeyboardModifier.ControlModifier)
    assert len(viewer.tables) == 1
    sheet = viewer.current_table
    qtbot.keyClick(sheet._qwidget._qtable_view, Qt.Key.Key_0)
    qtbot.keyClick(sheet._qwidget, Qt.Key.Key_Down)
    assert sheet.data.shape == (1, 1)
    assert sheet.cell[0, 0] == "0"

def test_movements_in_popup(make_tabulous_viewer, qtbot: QtBot):
    if sys.platform == "darwin":
        pytest.skip("Skipping test on macOS because it has a different focus policy.")
    viewer = make_tabulous_viewer()
    qtbot.addWidget(viewer._qwidget)
    sheet = viewer.add_spreadsheet(np.zeros((10, 10)))

    sheet.view_mode = "popup"
    popup = QtW.QApplication.focusWidget()
    qtbot.keyClick(popup, Qt.Key.Key_Down)
    qtbot.keyClick(popup, Qt.Key.Key_1)
    qtbot.keyClick(popup, Qt.Key.Key_Down)
    qtbot.keyClick(popup, Qt.Key.Key_Escape)

    assert popup is not QtW.QApplication.focusWidget()
    assert sheet.view_mode == "normal"
    assert sheet.cell[1, 0] == "1"

@pytest.mark.parametrize(
    "mode, key",
    [("popup", Qt.Key.Key_P), ("vertical", Qt.Key.Key_V), ("horizontal", Qt.Key.Key_H)]
)
def test_changing_view_mode(make_tabulous_viewer, qtbot: QtBot, mode, key):
    viewer = make_tabulous_viewer()
    qtbot.addWidget(viewer._qwidget)
    sheet = viewer.add_spreadsheet(np.zeros((10, 10)))

    assert sheet.view_mode == "normal"
    qtbot.keyClick(viewer._qwidget, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClick(viewer._qwidget, key)

    assert sheet.view_mode == mode

    qtbot.keyClick(viewer._qwidget, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClick(viewer._qwidget, Qt.Key.Key_N)
    assert sheet.view_mode == "normal"
