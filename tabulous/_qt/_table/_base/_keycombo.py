from ._table_base import QBaseTable, QMutableTable

QBaseTable._keymap.bind("Ctrl+C", QBaseTable.copyToClipboard, headers=False)
QBaseTable._keymap.bind("Ctrl+C, Ctrl+H", QBaseTable.copyToClipboard, headers=True)
QBaseTable._keymap.bind("Ctrl+H", QBaseTable.undoStackView)


@QBaseTable._keymap.bind("Ctrl+Up", row=0, column=None)
@QBaseTable._keymap.bind("Ctrl+Down", row=-1, column=None)
@QBaseTable._keymap.bind("Ctrl+Left", row=None, column=0)
@QBaseTable._keymap.bind("Ctrl+Right", row=None, column=-1)
def _(self: QBaseTable, row, column):
    if row is None:
        row = self._qtable_view.currentIndex().row()
    if column is None:
        column = self._qtable_view.currentIndex().column()
    self.moveToItem(row, column)
    self.setSelections([(row, column)])


@QBaseTable._keymap.bind("Ctrl+Shift+Up")
def _(self: QBaseTable):
    selection = self.selections()
    if len(selection) == 0:
        return None

    qtable = self._qtable_view
    last_selection = selection[-1]
    sl_row, sl_col = last_selection
    if self._qtable_view._last_shift_on is None:
        sl_row = slice(0, sl_row.stop)
    else:
        sl_row = slice(0, self._qtable_view._last_shift_on[0] + 1)
    c0 = qtable.currentIndex().column()
    self.setSelections([(sl_row, sl_col)])
    self.moveToItem(0, c0)


@QBaseTable._keymap.bind("Ctrl+Shift+Down")
def _(self: QBaseTable):
    selection = self.selections()
    if len(selection) == 0:
        return None

    qtable = self._qtable_view
    last_selection = selection[-1]

    nr = self.dataShape()[0]
    sl_row, sl_col = last_selection
    if self._qtable_view._last_shift_on is None:
        sl_row = slice(sl_row.start, nr)
    else:
        sl_row = slice(self._qtable_view._last_shift_on[0], nr)
    c0 = qtable.currentIndex().column()
    self.setSelections([(sl_row, sl_col)])
    self.moveToItem(nr - 1, c0)


@QBaseTable._keymap.bind("Ctrl+Shift+Left")
def _(self: QBaseTable):
    selection = self.selections()
    if len(selection) == 0:
        return None

    qtable = self._qtable_view
    last_selection = selection[-1]

    sl_row, sl_col = last_selection
    if self._qtable_view._last_shift_on is None:
        sl_col = slice(0, sl_col.stop)
    else:
        sl_col = slice(0, self._qtable_view._last_shift_on[1] + 1)

    r0 = qtable.currentIndex().row()
    self.setSelections([(sl_row, sl_col)])
    self.moveToItem(r0, 0)


@QBaseTable._keymap.bind("Ctrl+Shift+Right")
def _(self: QBaseTable):
    selection = self.selections()
    if len(selection) == 0:
        return None

    qtable = self._qtable_view
    last_selection = selection[-1]

    nc = self.dataShape()[1]
    sl_row, sl_col = last_selection
    if self._qtable_view._last_shift_on is None:
        sl_col = slice(sl_col.start, nc)
    else:
        sl_col = slice(self._qtable_view._last_shift_on[1], nc)

    r0 = qtable.currentIndex().row()
    self.setSelections([(sl_row, sl_col)])
    self.moveToItem(r0, nc - 1)


@QMutableTable._keymap.bind("Ctrl+X")
def _(self: QMutableTable):
    self.copyToClipboard(headers=False)
    return self.deleteValues()


QMutableTable._keymap.bind("Ctrl+V", QMutableTable.pasteFromClipBoard)
QMutableTable._keymap.bind("Delete", QMutableTable.deleteValues)
QMutableTable._keymap.bind("Backspace", QMutableTable.deleteValues)
QMutableTable._keymap.bind("Ctrl+Z", QMutableTable.undo)
QMutableTable._keymap.bind("Ctrl+Y", QMutableTable.redo)
