from ._table_base import QBaseTable, QMutableTable
from tabulous.exceptions import TriggerParent


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


# Following key combos are only available when the table is not in a viewer
def _check_no_viewer(func):
    def _wrapped(self: QBaseTable, **kwargs):
        if self.parentViewer() is None:
            func(self, **kwargs)
        else:
            raise TriggerParent

    return _wrapped


QBaseTable._keymap.bind("Ctrl+C", headers=False)(
    _check_no_viewer(QBaseTable.copyToClipboard)
)
QBaseTable._keymap.bind("Ctrl+C, Ctrl+H", headers=True)(
    _check_no_viewer(QBaseTable.copyToClipboard)
)
QBaseTable._keymap.bind("Ctrl+V")(_check_no_viewer(QBaseTable.pasteFromClipBoard))
QBaseTable._keymap.bind("Delete")(_check_no_viewer(QBaseTable.deleteValues))
QBaseTable._keymap.bind("Backspace")(_check_no_viewer(QBaseTable.deleteValues))
QBaseTable._keymap.bind("Ctrl+K, P")(_check_no_viewer(QBaseTable.setPopupView))
QBaseTable._keymap.bind("Ctrl+K, V", orientation="vertical")(
    _check_no_viewer(QBaseTable.setDualView)
)
QBaseTable._keymap.bind("Ctrl+K, H", orientation="horizontal")(
    _check_no_viewer(QBaseTable.setDualView)
)
QBaseTable._keymap.bind("Ctrl+K, N")(_check_no_viewer(QBaseTable.resetViewMode))
QBaseTable._keymap.bind("Ctrl+H")(_check_no_viewer(QBaseTable.undoStackView))
QBaseTable._keymap.bind("Menu")(_check_no_viewer(QBaseTable.showContextMenuAtIndex))
QBaseTable._keymap.bind("F6")(_check_no_viewer(QBaseTable.raiseSlotError))
QMutableTable._keymap.bind("Ctrl+Z")(_check_no_viewer(QMutableTable.undo))
QMutableTable._keymap.bind("Ctrl+Y")(_check_no_viewer(QMutableTable.redo))


@QBaseTable._keymap.bind("Ctrl+K, E")
@_check_no_viewer
def _(self: QBaseTable):
    try:
        self.setEditable(not self.isEditable())
    except Exception:
        pass


@QBaseTable._keymap.bind("Ctrl+X")
@_check_no_viewer
def _(self: QBaseTable):
    self.copyToClipboard(headers=False)
    self.deleteValues()


@QBaseTable._keymap.bind("Ctrl+S")
@_check_no_viewer
def _(self: QBaseTable):
    from tabulous import _io
    from tabulous._qt._history import QtFileHistoryManager

    if path := QtFileHistoryManager.requestPath("w", "Save table"):
        _io.save_file(path, self.getDataFrame())

    # (table.show_finder_widget, "Ctrl+F"),
