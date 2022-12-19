from __future__ import annotations
from typing import Iterator, NamedTuple

from . import file, plot, selection, tab, table, view, analysis, window
from types import FunctionType, ModuleType

_SUB_MODULES: list[ModuleType] = [
    file,
    plot,
    selection,
    tab,
    table,
    view,
    analysis,
    window,
]


class CommandInfo(NamedTuple):
    module: str
    desc: str
    command: FunctionType


def iter_commands() -> Iterator[tuple[str, FunctionType]]:
    for mod in _SUB_MODULES:
        for obj in vars(mod).values():
            if isinstance(obj, FunctionType) and not obj.__name__.startswith("_"):
                yield mod.__name__.split(".")[-1], obj


DEFAULT_KEYBINDING_SETTING: list[tuple[FunctionType, str]] = [
    (window.toggle_toolbar, "Ctrl+K, Ctrl+T"),
    (window.toggle_console, "Ctrl+Shift+C"),
    (window.show_command_palette, "Ctrl+Shift+P"),
    (window.focus_table, "Ctrl+0"),
    (window.new_window, "Ctrl+Shift+N"),
    (window.toggle_fullscreen, "F11"),
    (window.close_window, "Ctrl+W"),
    (window.show_keymap, "Ctrl+K, Shift+?"),
    (window.toggle_focus, "Ctrl+Shift+F"),
    (tab.activate_left, "Alt+Left"),
    (tab.activate_right, "Alt+Right"),
    (tab.swap_tab_with_left, "Alt+Shift+Left"),
    (tab.swap_tab_with_right, "Alt+Shift+Right"),
    (tab.tile_with_adjacent_table, "Ctrl+K, ^"),
    (tab.untile_table, "Ctrl+K, \\"),
    (view.set_popup_mode, "Ctrl+K, P"),
    (view.set_dual_v_mode, "Ctrl+K, V"),
    (view.set_dual_h_mode, "Ctrl+K, H"),
    (view.reset_view_mode, "Ctrl+K, N"),
    (table.toggle_editability, "Ctrl+K, E"),
    (table.new_spreadsheet, "Ctrl+N"),
    (table.show_finder_widget, "Ctrl+F"),
    (table.delete_table, "Ctrl+Delete"),
    (table.show_undo_stack_view, "Ctrl+H"),
    (table.undo_table, "Ctrl+Z"),
    (table.redo_table, "Ctrl+Y"),
    (file.open_table, "Ctrl+O"),
    (file.open_spreadsheet, "Ctrl+K, Ctrl+O"),
    (file.save_table, "Ctrl+S"),
    (selection.show_context_menu, "Menu"),
    (selection.raise_slot_error, "F6"),
    (selection.copy_data_tab_separated, "Ctrl+C"),
    (selection.copy_data_with_header_tab_separated, "Ctrl+C, Ctrl+H"),
    (selection.copy_as_new_table, "Ctrl+Shift+X"),
    (selection.select_all, "Ctrl+A"),
    (selection.cut_data, "Ctrl+X"),
    (selection.paste_data_tab_separated, "Ctrl+V"),
    (selection.delete_values, ["Delete", "Backspace"]),
]