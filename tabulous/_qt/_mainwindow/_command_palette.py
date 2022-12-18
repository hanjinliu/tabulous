from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable
from qt_command_palette import get_palette
from tabulous import commands as cmds

if TYPE_CHECKING:
    from ._base import _QtMainWidgetBase
    from tabulous.widgets import TableViewerBase
    from tabulous._qt._table import QSpreadSheet

palette = get_palette("tabulous")

default_group = palette.add_group("")
file_group = palette.add_group("File")
table_group = palette.add_group("Table")
analysis_group = palette.add_group("Analysis")
view_group = palette.add_group("View")
plot_group = palette.add_group("Plot")
selection_group = palette.add_group("Selection")
spreadsheet_group = palette.add_group("Spreadsheet")


def _command_to_function(
    f: Callable[[TableViewerBase], Any]
) -> Callable[[_QtMainWidgetBase], Any]:
    def wrapper(self: _QtMainWidgetBase):
        return f(self._table_viewer)

    wrapper.__doc__ = f.__doc__
    return wrapper


# fmt: off

for cmd, desc in [
    (cmds.window.show_keymap, "Show key map widget"),
    (cmds.window.close_window, "Close window"),
    (cmds.window.new_window, "New window"),
    (cmds.window.toggle_toolbar, "Toggle toolbar visibility"),
    (cmds.window.toggle_fullscreen, "Toggle fullscreen"),
    (cmds.table.undo_table, "Undo table"),
    (cmds.table.redo_table, "Redo table"),
]:
    default_group.register(_command_to_function(cmd), desc=desc)


for cmd, desc in [
    (cmds.io.open_table, "Open a file as a table"),
    (cmds.io.open_spreadsheet, "Open a file as a spreadsheet"),
    (cmds.io.save_table, "Save current table/spreadsheet"),
    (cmds.io.open_sample, "Open sample data"),
]:
    file_group.register(_command_to_function(cmd), desc=desc)

for cmd, desc in [
    (cmds.table.copy_as_table, "Copy current table as a new Table"),
    (cmds.table.copy_as_spreadsheet, "Copy current table as a new Spreadsheet"),
    (cmds.table.groupby, "Group by column(s)"),
    (cmds.table.switch_header, "Switch header and the top row"),
    (cmds.table.concat, "Concatenate tables"),
    (cmds.table.pivot, "Pivot current table"),
    (cmds.table.melt, "Melt (unpivot) current table"),
    (cmds.table.show_finder_widget, "Find item"),
    (cmds.table.sort_table, "Sort table"),
    (cmds.table.random, "Generate random values"),
]:
    table_group.register(_command_to_function(cmd), desc=desc)


for cmd, desc in [
    (cmds.analysis.summarize_table, "Summarize table"),
    (cmds.analysis.show_eval_widget, "Evaluate expression on current table"),
    (cmds.analysis.show_filter_widget, "Filter current table"),
    (cmds.analysis.show_optimizer_widget, "Open optimizer widget"),
    (cmds.analysis.show_stats_widget, "Open statistics test widget"),
    (cmds.analysis.show_sklearn_widget, "Open scikit-learn widget"),
    (cmds.analysis.toggle_console, "Toggle QtConsole"),
]:
    analysis_group.register(_command_to_function(cmd), desc=desc)

for cmd, desc in [
    (cmds.view.set_popup_mode, "Popup table"),
    (cmds.view.set_dual_h_mode, "Dual-view table horizontally"),
    (cmds.view.set_dual_v_mode, "Dual-view table vertically"),
    (cmds.view.reset_view_mode, "Reset table view mode"),
    (cmds.view.tile_tables, "Tile tables"),
    (cmds.view.untile_table, "Untile tables"),
]:
    view_group.register(_command_to_function(cmd), desc=desc)

for cmd, desc in [
    (cmds.plot.plot, "Run plt.plot"),
    (cmds.plot.scatter, "Run plt.scatter"),
    (cmds.plot.errorbar, "Run plt.errorbar"),
    (cmds.plot.hist, "Run plt.hist"),
    (cmds.plot.swarmplot, "Run sns.swarmplot"),
    (cmds.plot.barplot, "Run sns.barplot"),
    (cmds.plot.boxplot, "Run sns.boxplot"),
    (cmds.plot.boxenplot, "Run sns.boxenplot"),
    (cmds.plot.new_figure, "Create a new figure canvas"),
]:
    plot_group.register(_command_to_function(cmd), desc=desc)


for cmd, desc in [
    (cmds.table.copy_data_tab_separated, "Copy cells (tab separated)"),
    (cmds.table.copy_data_with_header_tab_separated, "Copy cells with headers (tab separated)"),
    (cmds.table.copy_data_comma_separated, "Copy cells (comma separated)"),
    (cmds.table.copy_data_with_header_comma_separated, "Copy cells with headers (comma separated)"),
    (cmds.table.copy_as_new_table, "Copy as a new table"),
    (cmds.table.copy_as_new_spreadsheet, "Copy as a new spreadsheet"),
    (cmds.table.copy_as_literal, "Copy as literal"),
    (cmds.table.paste_data_tab_separated, "Paste from tab separated text"),
    (cmds.table.paste_data_comma_separated, "Paste from comma separated text"),
    (cmds.table.paste_data_from_numpy_string, "Paste from numpy-style text"),
    (cmds.table.select_all, "Select all the cells"),
    (cmds.table.cut_data, "Cut selected cells"),
    (cmds.table.delete_values, "Delete selected cells"),
    (cmds.table.add_highlight, "Add highlight to selected cells"),
    (cmds.table.insert_row_above, "Insert row above current index"),
    (cmds.table.insert_row_below, "Insert row below current index"),
    (cmds.table.insert_column_left, "Insert column left of current index"),
    (cmds.table.insert_column_right, "Insert column right of current index"),
    (cmds.table.remove_this_row, "Remove current row"),
    (cmds.table.remove_this_column, "Remove current column"),
    (cmds.table.set_column_dtype, "Set column dtype"),
    (cmds.table.set_foreground_colormap, "Set foreground colormap"),
    (cmds.table.set_background_colormap, "Set background colormap"),
    (cmds.table.reset_foreground_colormap, "Reset foreground colormap"),
    (cmds.table.reset_background_colormap, "Reset background colormap"),
    (cmds.table.set_text_formatter, "Set text formatter"),
    (cmds.table.reset_text_formatter, "Reset text formatter"),
]:
    selection_group.register(_command_to_function(cmd), desc=desc)

# fmt: on
