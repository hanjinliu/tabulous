from __future__ import annotations
from ._mainwidgets import QMainWindow, QMainWidget, _QtMainWidgetBase
from tabulous import commands as cmds

# fmt: off

@QMainWidget._keymap.bind("Ctrl+K")
@QMainWindow._keymap.bind("Ctrl+K")
def _(self: _QtMainWidgetBase):
    """Basic sequence to trigger key combo."""
    return self.setFocus()


@QMainWidget._keymap.bind("Ctrl+K, Ctrl+T")
@QMainWindow._keymap.bind("Ctrl+K, Ctrl+T")
def _(self: _QtMainWidgetBase):
    """Toggle toolbar visibility."""
    cmds.window.toggle_toolbar(self._table_viewer)

@QMainWidget._keymap.bind("Ctrl+K, E")
@QMainWindow._keymap.bind("Ctrl+K, E")
def _(self: _QtMainWidgetBase):
    """Toggle table editability."""
    cmds.table.toggle_editability(self._table_viewer)


@QMainWidget._keymap.bind("Ctrl+K, V", mode="vertical", desc="Vertical dual view mode.")
@QMainWindow._keymap.bind("Ctrl+K, V", mode="vertical", desc="Vertical dual view mode.")
@QMainWidget._keymap.bind("Ctrl+K, H", mode="horizontal", desc="Horizontal dual view mode.")
@QMainWindow._keymap.bind("Ctrl+K, H", mode="horizontal", desc="Horizontal dual view mode.")
@QMainWidget._keymap.bind("Ctrl+K, P", mode="popup", desc="Popup view mode.")
@QMainWindow._keymap.bind("Ctrl+K, P", mode="popup", desc="Popup view mode.")
@QMainWidget._keymap.bind("Ctrl+K, N", mode="normal", desc="Reset view mode.")
@QMainWindow._keymap.bind("Ctrl+K, N", mode="normal", desc="Reset view mode.")
def _(self: _QtMainWidgetBase, mode):
    self._table_viewer.current_table.view_mode = mode
    return None

@QMainWindow._keymap.bind("Ctrl+Shift+C")
def _(self: _QtMainWidgetBase):
    """Toggle embeded console visibility."""
    cmds.window.toggle_console(self._table_viewer)


@QMainWidget._keymap.bind("Ctrl+Shift+P")
@QMainWindow._keymap.bind("Ctrl+Shift+P")
@QMainWidget._keymap.bind("F1")
@QMainWindow._keymap.bind("F1")
def _(self: _QtMainWidgetBase):
    """Show command palette."""
    cmds.window.show_command_palette(self._table_viewer)

@QMainWidget._keymap.bind("Ctrl+0")
@QMainWindow._keymap.bind("Ctrl+0")
def _(self: _QtMainWidgetBase):
    """Focus on a cell in the current table."""
    cmds.window.focus_table(self._table_viewer)


@QMainWidget._keymap.bind("Ctrl+Shift+F")
@QMainWindow._keymap.bind("Ctrl+Shift+F")
def _(self: _QtMainWidgetBase):
    """Move focus between table and console."""
    table = self._table_viewer.current_table
    if table is None:
        return
    if table._qwidget._qtable_view.hasFocus():
        console = self._console_widget
        if console is not None and console.isActive():
            console.setFocus()
    else:
        self.setCellFocus()
    return


@QMainWidget._keymap.bind("Ctrl+I")
@QMainWindow._keymap.bind("Ctrl+I")
def _(self: _QtMainWidgetBase):
    """Insert data reference to the console."""
    console = self._console_widget
    if console is not None and console.isActive():
        console.setTempText(f"{console._current_data_identifier}[...]")
    return None

@QMainWidget._keymap.bind("Ctrl+N")
@QMainWindow._keymap.bind("Ctrl+N")
def _(self: _QtMainWidgetBase):
    """New spreadsheet"""
    cmds.table.new_spreadsheet(self._table_viewer)


@QMainWindow._keymap.bind("Ctrl+Shift+N")
def _(self: _QtMainWidgetBase):
    """New window"""
    cmds.window.new_window(self._table_viewer)

@QMainWidget._keymap.bind("Ctrl+O")
@QMainWindow._keymap.bind("Ctrl+O")
def _(self: _QtMainWidgetBase):
    """Open a file as a table."""
    cmds.io.open_table(self._table_viewer)

@QMainWidget._keymap.bind("Ctrl+K, Ctrl+O")
@QMainWindow._keymap.bind("Ctrl+K, Ctrl+O")
def _(self: _QtMainWidgetBase):
    """Open a file as a table."""
    cmds.io.open_spreadsheet(self._table_viewer)


@QMainWidget._keymap.bind("Ctrl+S")
@QMainWindow._keymap.bind("Ctrl+S")
def _(self: _QtMainWidgetBase):
    """Save current table."""
    cmds.io.save_table(self._table_viewer)


@QMainWindow._keymap.bind("Alt")
def _(self: _QtMainWidgetBase):
    """Move focus to toolbar."""
    self._toolbar.showTabTooltips()
    self.setFocus()


@QMainWindow._keymap.bind("Alt, F", index=0, desc="Move focus to `File` menu tab.")
@QMainWindow._keymap.bind("Alt, T", index=1, desc="Move focus to `Table` menu tab.")
@QMainWindow._keymap.bind("Alt, A", index=2, desc="Move focus to `Analyze` menu tab.")
@QMainWindow._keymap.bind("Alt, V", index=3, desc="Move focus to `View` menu tab.")
@QMainWindow._keymap.bind("Alt, P", index=4, desc="Move focus to `Plot` menu tab.")
def _(self: QMainWindow, index: int):
    self._toolbar.setCurrentIndex(index)
    self._toolbar.currentToolBar().showTabTooltips()


@QMainWindow._keymap.bind("Alt, F, {}")
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


@QMainWindow._keymap.bind("Ctrl+Tab")
def _(self: QMainWindow):
    """Activate the new tab."""
    num = self._tablestack.count()
    if num == 0:
        return None
    idx = self._tablestack.currentIndex() + 1
    if idx >= num:
        idx = 0
    return self._tablestack.setCurrentIndex(idx)


@QMainWidget._keymap.bind("Ctrl+K, Shift+?")
@QMainWindow._keymap.bind("Ctrl+K, Shift+?")
def _(self: _QtMainWidgetBase):
    """Open a keymap viewer."""
    cmds.window.show_keymap(self._table_viewer)

@QMainWidget._keymap.bind("Alt+Left")
@QMainWindow._keymap.bind("Alt+Left")
def _(self: _QtMainWidgetBase):
    """Activate the previous table."""
    cmds.tab.activate_left(self._table_viewer)

@QMainWidget._keymap.bind("Alt+Right")
@QMainWindow._keymap.bind("Alt+Right")
def _(self: _QtMainWidgetBase):
    """Activate the next table."""
    cmds.tab.activate_right(self._table_viewer)

@QMainWidget._keymap.bind("Alt+Shift+Left")
@QMainWindow._keymap.bind("Alt+Shift+Left")
def _(self: _QtMainWidgetBase):
    """Swap the current table with the previous one."""
    cmds.tab.swap_tab_with_left(self._table_viewer)


@QMainWidget._keymap.bind("Alt+Shift+Right")
@QMainWindow._keymap.bind("Alt+Shift+Right")
def _(self: _QtMainWidgetBase):
    """Swap the current table with the next one."""
    cmds.tab.swap_tab_with_right(self._table_viewer)

@QMainWidget._keymap.bind("Ctrl+F")
@QMainWindow._keymap.bind("Ctrl+F")
def _(self: _QtMainWidgetBase):
    """Open finder."""
    cmds.table.show_finder_widget(self._table_viewer)

@QMainWidget._keymap.bind("Ctrl+K, ^")
@QMainWindow._keymap.bind("Ctrl+K, ^")
def _(self: _QtMainWidgetBase):
    """Tile tables."""
    cmds.tab.tile_with_adjacent_table(self._table_viewer)

@QMainWidget._keymap.bind("Ctrl+K, \\")
@QMainWindow._keymap.bind("Ctrl+K, \\")
def _(self: _QtMainWidgetBase):
    """Untile tables."""
    cmds.tab.untile_table(self._table_viewer)

@QMainWindow._keymap.bind("F11")
def _(self: QMainWindow):
    """Toggle fullscreen mode."""
    cmds.window.toggle_fullscreen(self._table_viewer)

@QMainWindow._keymap.bind("Ctrl+W")
def _(self: QMainWindow):
    """Close the window."""
    return self.close(ask=None)

@QMainWindow._keymap.bind("Ctrl+Delete")
def _(self: QMainWindow):
    """Delete the current table."""
    cmds.table.delete_table(self._table_viewer)

# fmt: on
