from ._table_base import QBaseTable, QMutableTable

QBaseTable._keymap.bind("Ctrl+C", QBaseTable.copyToClipboard, headers=False)
QBaseTable._keymap.bind("Ctrl+C, Ctrl+H", QBaseTable.copyToClipboard, headers=True)
QBaseTable._keymap.bind("Ctrl+H", QBaseTable.undoStackView)


@QBaseTable._keymap.bind("Ctrl+Up", row=0, column=None)
@QBaseTable._keymap.bind("Ctrl+Down", row=-1, column=None)
@QBaseTable._keymap.bind("Ctrl+Left", row=None, column=0)
@QBaseTable._keymap.bind("Ctrl+Right", row=None, column=-1)
@QBaseTable._keymap.bind("Ctrl+Shift+Up", row=0, column=None)
@QBaseTable._keymap.bind("Ctrl+Shift+Down", row=-1, column=None)
@QBaseTable._keymap.bind("Ctrl+Shift+Left", row=None, column=0)
@QBaseTable._keymap.bind("Ctrl+Shift+Right", row=None, column=-1)
def _(self: QBaseTable, row, column):
    return self.moveToItem(row, column)


@QBaseTable._keymap.bind("Ctrl+A")
def _(self: QBaseTable):
    model = self._qtable_view.model()
    rsel = slice(0, model.rowCount())
    csel = slice(0, model.columnCount())
    return self.setSelections([(rsel, csel)])


@QBaseTable._keymap.bind("Ctrl+Alt+Up", dr=-1, dc=0)
@QBaseTable._keymap.bind("Ctrl+Alt+Down", dr=1, dc=0)
@QBaseTable._keymap.bind("Ctrl+Alt+Left", dr=0, dc=-1)
@QBaseTable._keymap.bind("Ctrl+Alt+Right", dr=0, dc=1)
@QBaseTable._keymap.bind("Ctrl+Alt+PageUp", dr=-5, dc=0)
@QBaseTable._keymap.bind("Ctrl+Alt+PageDown", dr=5, dc=0)
@QBaseTable._keymap.bind("Ctrl+Alt+Home", dr=0, dc=-5)
@QBaseTable._keymap.bind("Ctrl+Alt+End", dr=0, dc=5)
def _(self: QBaseTable, dr, dc):
    """Scroll without moving the selection."""
    vbar = self._qtable_view.verticalScrollBar()
    hbar = self._qtable_view.horizontalScrollBar()
    dv = dr * 75 * self._qtable_view._zoom
    dh = dc * 75 * self._qtable_view._zoom
    vbar.setValue(max(vbar.minimum(), min(vbar.maximum(), vbar.value() + dv)))
    hbar.setValue(max(hbar.minimum(), min(hbar.maximum(), hbar.value() + dh)))


@QMutableTable._keymap.bind("Ctrl+X")
def _(self: QMutableTable):
    self.copyToClipboard(headers=False)
    return self.deleteValues()


QMutableTable._keymap.bind("Ctrl+V", QMutableTable.pasteFromClipBoard)
QMutableTable._keymap.bind("Delete", QMutableTable.deleteValues)
QMutableTable._keymap.bind("Backspace", QMutableTable.deleteValues)
QMutableTable._keymap.bind("Ctrl+Z", QMutableTable.undo)
QMutableTable._keymap.bind("Ctrl+Y", QMutableTable.redo)
