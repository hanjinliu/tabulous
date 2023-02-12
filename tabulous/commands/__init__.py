from __future__ import annotations

from typing import Any, Callable, Iterator, TYPE_CHECKING

from . import file, plot, column, selection, tab, table, view, analysis, window
from types import FunctionType, ModuleType
from qt_command_palette import get_palette

if TYPE_CHECKING:
    from tabulous._qt._mainwindow import _QtMainWidgetBase
    from tabulous.widgets import TableViewerBase

_SUB_MODULES: list[ModuleType] = [
    file,
    plot,
    column,
    selection,
    tab,
    table,
    view,
    analysis,
    window,
]

__all__ = [mod.__name__.split(".")[-1] for mod in _SUB_MODULES] + [
    "iter_commands",
    "register_command",
]


def iter_commands() -> Iterator[tuple[str, FunctionType]]:
    for mod in _SUB_MODULES:
        for obj in vars(mod).values():
            if isinstance(obj, FunctionType) and not obj.__name__.startswith("_"):
                yield mod.__name__.split(".")[-1], obj


def register_command(
    func: Callable = None,
    title: str = "User defined",
    desc: str = None,
) -> Callable[[Callable[[TableViewerBase], Any]], Callable[[TableViewerBase], Any]]:
    def wrapper(f):
        palette = get_palette("tabulous")
        if desc is None:
            fname = getattr(f, "__name__", None)
            if not isinstance(fname, str):
                raise TypeError(
                    f"Expected str for the function name, got {type(fname).__name__}"
                )
            _desc = fname.title().replace("_", " ")
        else:
            _desc = desc

        def fn(self: _QtMainWidgetBase):
            return f(self._table_viewer)

        fn.__doc__ = f.__doc__
        fn.__name__ = f.__name__
        palette.register(fn, title=title, desc=_desc)
        palette.update()
        return f

    return wrapper if func is None else wrapper(func)


DEFAULT_KEYBINDING_SETTING: list[tuple[FunctionType, str]] = [
    (window.toggle_toolbar, "Ctrl+K, Ctrl+T"),
    (window.toggle_console, "Ctrl+Shift+C"),
    (window.show_command_palette, ["F1", "Ctrl+Shift+P"]),
    (window.focus_table, "Ctrl+0"),
    (window.new_window, "Ctrl+Shift+N"),
    (window.toggle_fullscreen, "F11"),
    (window.close_window, "Ctrl+W"),
    (window.show_keymap, "Ctrl+K, Shift+?"),
    (window.toggle_focus, "Ctrl+Shift+F"),
    (window.show_preference, "Ctrl+,"),
    (tab.activate_left, "Alt+Left"),
    (tab.activate_right, "Alt+Right"),
    (tab.swap_tab_with_left, "Alt+Shift+Left"),
    (tab.swap_tab_with_right, "Alt+Shift+Right"),
    (tab.tile_with_adjacent_table, "Ctrl+K, ^"),
    (tab.untile_table, "Ctrl+K, \\"),
    (tab.delete_tab, "Ctrl+Delete"),
    (view.set_popup_mode, "Ctrl+K, P"),
    (view.set_dual_v_mode, "Ctrl+K, V"),
    (view.set_dual_h_mode, "Ctrl+K, H"),
    (view.reset_view_mode, "Ctrl+K, N"),
    (table.toggle_editability, "Ctrl+K, E"),
    (table.new_spreadsheet, "Ctrl+N"),
    (table.show_finder_widget, "Ctrl+F"),
    (table.show_undo_stack_view, "Ctrl+H"),
    (table.undo_table, "Ctrl+Z"),
    (table.redo_table, "Ctrl+Y"),
    (file.open_table, "Ctrl+O"),
    (file.open_spreadsheet, "Ctrl+K, Ctrl+O"),
    (file.save_table, "Ctrl+S"),
    (file.save_table_to_source, "Ctrl+Shift+S"),
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
