from tabulous.widgets import Table, SpreadSheet
from pytestqt.qtbot import QtBot
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import Qt
import numpy as np

DATA = np.arange(36).reshape(9, 4)

def test_selection_move(qtbot: QtBot):
    table = Table(DATA.copy(), editable=True)
    qtbot.addWidget(table.native)
    qtbot.keyClick(table.native, Qt.Key.Key_Down)
    assert table.selections[0] == (slice(1, 2), slice(0, 1))

def test_copy_paste(qtbot: QtBot):
    table = Table(DATA.copy(), editable=True)
    qtbot.addWidget(table.native)

    # copy
    table.selections = [(slice(0, 1), slice(0, 1))]
    qtbot.keyClick(table.native, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)

    # paste
    table.selections = [(slice(0, 5), slice(1, 2))]
    qtbot.keyClick(table.native, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)

    assert (table.data.iloc[0:5, 1:2] == table.data.iloc[0, 0]).all().all()

def test_cut_paste(qtbot: QtBot):
    table = SpreadSheet(DATA.copy(), editable=True)
    qtbot.addWidget(table.native)

    # copy
    table.selections = [(slice(0, 1), slice(0, 1))]
    qtbot.keyClick(table.native, Qt.Key.Key_X, Qt.KeyboardModifier.ControlModifier)
    assert table.cell[0, 0] == ""

    # paste
    table.selections = [(slice(0, 5), slice(1, 2))]
    qtbot.keyClick(table.native, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)

    assert (table.data.iloc[0:5, 1:2] == 0).all().all()

def test_undo_redo(qtbot: QtBot):
    table = Table(DATA.copy(), editable=True)
    qtbot.addWidget(table.native)

    assert table.data.iloc[0, 0] == 0
    table.cell[0, 0] = -1
    assert table.data.iloc[0, 0] == -1
    qtbot.keyClick(table.native, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert table.data.iloc[0, 0] == 0
    qtbot.keyClick(table.native, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    assert table.data.iloc[0, 0] == -1

def test_erase(qtbot: QtBot):
    sheet = SpreadSheet(DATA.copy(), editable=True)
    qtbot.addWidget(sheet.native)

    assert sheet.cell[0, 0] != ""
    sheet.selections = [(slice(0, 1), slice(0, 1))]
    qtbot.keyClick(sheet.native, Qt.Key.Key_Backspace)
    assert sheet.cell[0, 0] == ""
    sheet.selections = [(slice(0, 1), slice(1, 2))]
    assert sheet.cell[0, 1] != ""
    qtbot.keyClick(sheet.native, Qt.Key.Key_Delete)
    assert sheet.cell[0, 1] == ""

def test_slot():
    sheet = SpreadSheet({"a": [1, 3, 5]})
    sheet.cell[0, 1] = "&=np.mean(df.iloc[:, 0])"
    assert sheet.cell[0, 1] == "3.0"
    sheet.cell[0, 0] = 4
    assert sheet.cell[0, 1] == "4.0"
