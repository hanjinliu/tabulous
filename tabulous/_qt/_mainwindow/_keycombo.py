from __future__ import annotations

from ._mainwidgets import QMainWindow, QMainWidget, _QtMainWidgetBase

# fmt: off

@QMainWidget._keymap.bind("Ctrl+K")
@QMainWindow._keymap.bind("Ctrl+K")
def _(self: _QtMainWidgetBase):
    """Basic sequence to trigger key combo."""
    return self.setFocus()


@QMainWindow._keymap.bind("Alt")
def _(self: _QtMainWidgetBase):
    """Move focus to toolbar."""
    self._toolbar.showTabTooltips()
    self.setFocus()


@QMainWindow._keymap.bind("Alt, H", index=0, desc="Move focus to `Home` menu tab.")
@QMainWindow._keymap.bind("Alt, E", index=1, desc="Move focus to `Edit` menu tab.")
@QMainWindow._keymap.bind("Alt, T", index=2, desc="Move focus to `Table` menu tab.")
@QMainWindow._keymap.bind("Alt, A", index=3, desc="Move focus to `Analyze` menu tab.")
@QMainWindow._keymap.bind("Alt, V", index=4, desc="Move focus to `View` menu tab.")
@QMainWindow._keymap.bind("Alt, P", index=5, desc="Move focus to `Plot` menu tab.")
def _(self: QMainWindow, index: int):
    self._toolbar.setCurrentIndex(index)
    self._toolbar.currentToolBar().showTabTooltips()


@QMainWindow._keymap.bind("Alt, H, {}")
@QMainWindow._keymap.bind("Alt, E, {}")
@QMainWindow._keymap.bind("Alt, T, {}")
@QMainWindow._keymap.bind("Alt, A, {}")
@QMainWindow._keymap.bind("Alt, V, {}")
@QMainWindow._keymap.bind("Alt, P, {}")
def _(self: QMainWindow, key: str):
    """Push a tool button at the given position."""
    try:
        index = int(key)
    except ValueError:
        return None

    self._toolbar.currentToolBar().clickButton((index - 1) % 10, ignore_index_error=True)

# fmt: on
