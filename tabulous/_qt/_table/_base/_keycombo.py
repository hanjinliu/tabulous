from ._table_base import QBaseTable


@QBaseTable._keymap.bind("Up", dr=-1, dc=0)
@QBaseTable._keymap.bind("Down", dr=1, dc=0)
@QBaseTable._keymap.bind("Left", dr=0, dc=-1)
@QBaseTable._keymap.bind("Right", dr=0, dc=1)
@QBaseTable._keymap.bind("PageUp", dr=-10, dc=0)
@QBaseTable._keymap.bind("PageDown", dr=10, dc=0)
@QBaseTable._keymap.bind("Home", dr=0, dc=-10)
@QBaseTable._keymap.bind("End", dr=0, dc=10)
def _(self: QBaseTable, dr, dc):
    return self._qtable_view._selection_model.move(dr, dc, allow_header=True)


@QBaseTable._keymap.bind("Shift+Up", dr=-1, dc=0)
@QBaseTable._keymap.bind("Shift+Down", dr=1, dc=0)
@QBaseTable._keymap.bind("Shift+Left", dr=0, dc=-1)
@QBaseTable._keymap.bind("Shift+Right", dr=0, dc=1)
@QBaseTable._keymap.bind("Shift+PageUp", dr=-10, dc=0)
@QBaseTable._keymap.bind("Shift+PageDown", dr=10, dc=0)
@QBaseTable._keymap.bind("Shift+Home", dr=0, dc=-10)
@QBaseTable._keymap.bind("Shift+End", dr=0, dc=10)
def _(self: QBaseTable, dr, dc):
    self._qtable_view._selection_model.set_shift(True)
    return self._qtable_view._selection_model.move(dr, dc)


@QBaseTable._keymap.bind("Ctrl+Up", row=0, column=None)
@QBaseTable._keymap.bind("Ctrl+Down", row=-1, column=None)
@QBaseTable._keymap.bind("Ctrl+Left", row=None, column=0)
@QBaseTable._keymap.bind("Ctrl+Right", row=None, column=-1)
@QBaseTable._keymap.bind("Ctrl+Shift+Up", row=0, column=None)
@QBaseTable._keymap.bind("Ctrl+Shift+Down", row=-1, column=None)
@QBaseTable._keymap.bind("Ctrl+Shift+Left", row=None, column=0)
@QBaseTable._keymap.bind("Ctrl+Shift+Right", row=None, column=-1)
def _(self: QBaseTable, row, column):
    return self.moveToItem(row, column, clear_selection=False)


@QBaseTable._keymap.bind("Ctrl+Alt+Up", dr=-1, dc=0)
@QBaseTable._keymap.bind("Ctrl+Alt+Down", dr=1, dc=0)
@QBaseTable._keymap.bind("Ctrl+Alt+Left", dr=0, dc=-1)
@QBaseTable._keymap.bind("Ctrl+Alt+Right", dr=0, dc=1)
@QBaseTable._keymap.bind("Ctrl+Alt+PageUp", dr=-10, dc=0)
@QBaseTable._keymap.bind("Ctrl+Alt+PageDown", dr=10, dc=0)
@QBaseTable._keymap.bind("Ctrl+Alt+Home", dr=0, dc=-10)
@QBaseTable._keymap.bind("Ctrl+Alt+End", dr=0, dc=10)
def _(self: QBaseTable, dr, dc):
    """Scroll without moving the selection."""
    vbar = self._qtable_view.verticalScrollBar()
    hbar = self._qtable_view.horizontalScrollBar()
    dv = dr * 75 * self._qtable_view._zoom
    dh = dc * 75 * self._qtable_view._zoom
    vbar.setValue(max(vbar.minimum(), min(vbar.maximum(), vbar.value() + dv)))
    hbar.setValue(max(hbar.minimum(), min(hbar.maximum(), hbar.value() + dh)))
