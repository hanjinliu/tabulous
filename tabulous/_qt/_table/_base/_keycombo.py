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


@QBaseTable._keymap.bind("Shift+Up", dr=-1, dc=0)
@QBaseTable._keymap.bind("Shift+Down", dr=1, dc=0)
@QBaseTable._keymap.bind("Shift+Left", dr=0, dc=-1)
@QBaseTable._keymap.bind("Shift+Right", dr=0, dc=1)
def _(self: QBaseTable, dr, dc):
    index = self._qtable_view.currentIndex()
    r0, c0 = index.row(), index.column()
    nr, nc = self.tableShape()
    r1 = r0 + dr if 0 <= r0 + dr < nr else r0
    c1 = c0 + dc if 0 <= c0 + dc < nc else c0
    self.moveToItem(r1, c1)

    if self._qtable_view._last_shift_on is None:
        sel = (slice(r0, r1 + 1), slice(c0, c1 + 1))
    else:
        r, c = self._qtable_view._last_shift_on
        _r0, _r1 = sorted([r1, r])
        _c0, _c1 = sorted([c1, c])
        sel = (slice(_r0, _r1 + 1), slice(_c0, _c1 + 1))
    self.setSelections([(sel)])


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
