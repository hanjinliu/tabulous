from tabulous import TableViewer
import numpy as np
from pytestqt.qtbot import QtBot
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

def test_add_spreadsheet_and_move(qtbot: QtBot):
    viewer = TableViewer()
    qtbot.addWidget(viewer._qwidget)
    qtbot.keyClick(viewer._qwidget, Qt.Key.Key_N, Qt.KeyboardModifier.ControlModifier)
    assert len(viewer.tables) == 1
    sheet = viewer.current_table
    qtbot.keyClick(sheet._qwidget._qtable_view, Qt.Key.Key_0)
    qtbot.keyClick(sheet._qwidget, Qt.Key.Key_Down)
    assert sheet.data.shape == (1, 1)
    assert sheet.cell[0, 0] == "0"

def test_movements_in_popup(qtbot: QtBot):
    viewer = TableViewer()
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
