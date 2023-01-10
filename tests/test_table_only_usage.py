from tabulous.widgets import Table
from pytestqt.qtbot import QtBot
from qtpy.QtCore import Qt
import numpy as np

DATA = np.arange(36).reshape(9, 4)

def test_selection_move(qtbot: QtBot):
    table = Table(DATA, editable=True)
    qtbot.addWidget(table.native)
    qtbot.keyClick(table.native, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
    assert table.selections[0] == (slice(1, 2), slice(0, 1))

def test_copy_paste(qtbot: QtBot):
    table = Table(DATA, editable=True)
    qtbot.addWidget(table.native)

    # copy
    table.selections = [(slice(0, 1), slice(0, 1))]
    qtbot.keyClick(table.native, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)

    # paste
    table.selections = [(slice(0, 5), slice(1, 2))]
    qtbot.keyClick(table.native, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)

    assert (table.data.iloc[0:5, 1:2] == table.data.iloc[0, 0]).all().all()

def test_undo_redo(qtbot: QtBot):
    table = Table(DATA, editable=True)
    qtbot.addWidget(table.native)

    assert table.data.iloc[0, 0] == 0
    table.cell[0, 0] = -1
    assert table.data.iloc[0, 0] == -1
    qtbot.keyClick(table.native, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert table.data.iloc[0, 0] == 0
    qtbot.keyClick(table.native, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    assert table.data.iloc[0, 0] == -1
