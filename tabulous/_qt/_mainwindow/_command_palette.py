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
    (cmds.table.copy_as_new_table, "Copy current table as a new Table"),
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
    (
        cmds.table.copy_data_with_header_tab_separated,
        "Copy cells with headers (tab separated)",
    ),
    (cmds.table.copy_data_comma_separated, "Copy cells (comma separated)"),
    (
        cmds.table.copy_data_with_header_comma_separated,
        "Copy cells with headers (comma separated)",
    ),
    (cmds.table.copy_as_new_table, "Copy as a new table"),
    (cmds.table.copy_as_spreadsheet, "Copy as a new spreadsheet"),
    (cmds.table.copy_as_literal, "Copy as literal"),
    (cmds.table.paste_data_tab_separated, "Paste from tab separated text"),
    (cmds.table.paste_data_comma_separated, "Paste from comma separated text"),
    (cmds.table.paste_data_from_numpy_string, "Paste from numpy-style text"),
    (cmds.table.select_all, "Select all the cells"),
    (cmds.table.cut_data, "Cut selected cells"),
    (cmds.table.delete_values, "Delete selected cells"),
    (cmds.table.add_highlight, "Add highlight to selected cells"),
]:
    selection_group.register(_command_to_function(cmd), desc=desc)


def _get_spreadsheet(self: _QtMainWidgetBase) -> QSpreadSheet:
    from tabulous._qt._table import QSpreadSheet

    qwidget = self._table_viewer.current_table._qwidget
    if isinstance(qwidget, QSpreadSheet):
        return qwidget
    raise TypeError("This action is only available for a Spreadsheet")


def _get_selected_column(qspreadsheet: QSpreadSheet) -> int:
    colsel = qspreadsheet._qtable_view._selection_model._col_selection_indices
    if len(colsel) == 0:
        raise ValueError("No columns selected")
    if len(colsel) > 1:
        raise ValueError("Multiple columns selected")
    idx = next(iter(colsel))
    rng = qspreadsheet._qtable_view._selection_model.ranges[idx]
    if rng[1].start != rng[1].stop - 1:
        raise ValueError("Multiple columns selected")

    return rng[1].start


@spreadsheet_group.register("Insert row above")
def insert_row_above(self: _QtMainWidgetBase):
    """Insert a row above the current selection"""
    qspreadsheet = _get_spreadsheet(self)
    qspreadsheet._insert_row_above(
        qspreadsheet._qtable_view._selection_model.current_index.row
    )


@spreadsheet_group.register("Insert row below")
def insert_row_below(self: _QtMainWidgetBase):
    """Insert a row below the current selection"""
    qspreadsheet = _get_spreadsheet(self)
    qspreadsheet._insert_row_below(
        qspreadsheet._qtable_view._selection_model.current_index.row
    )


@spreadsheet_group.register("Insert column left")
def insert_column_left(self: _QtMainWidgetBase):
    """Insert a column on the left side of the current selection"""
    qspreadsheet = _get_spreadsheet(self)
    qspreadsheet._insert_column_left(
        qspreadsheet._qtable_view._selection_model.current_index.column
    )


@spreadsheet_group.register("Insert column right")
def insert_column_right(self: _QtMainWidgetBase):
    """Insert a column on the right side of the current selection"""
    qspreadsheet = _get_spreadsheet(self)
    qspreadsheet._insert_column_right(
        qspreadsheet._qtable_view._selection_model.current_index.column
    )


@spreadsheet_group.register("Remove selected rows")
def remove_row(self: _QtMainWidgetBase):
    """Remove all the selected rows."""
    qspreadsheet = _get_spreadsheet(self)
    qspreadsheet._remove_selected_rows(
        qspreadsheet._qtable_view._selection_model.current_index.row
    )


@spreadsheet_group.register("Remove selected columns")
def remove_column(self: _QtMainWidgetBase):
    """Remove all the selected columns."""
    qspreadsheet = _get_spreadsheet(self)
    qspreadsheet._remove_selected_columns(
        qspreadsheet._qtable_view._selection_model.current_index.column
    )


@spreadsheet_group.register("Set column dtype")
def set_column_dtype(self: _QtMainWidgetBase):
    """Open a dialog to set the dtype to the selected column."""
    qspreadsheet = _get_spreadsheet(self)
    index = _get_selected_column(qspreadsheet)
    qspreadsheet._set_column_dtype_with_dialog(index)


@spreadsheet_group.register("Set foreground color")
def set_foreground_color(self: _QtMainWidgetBase):
    """Set the foreground color of the selected cells."""
    qspreadsheet = _get_spreadsheet(self)
    index = _get_selected_column(qspreadsheet)
    qspreadsheet._set_foreground_colormap_with_dialog(index)


@spreadsheet_group.register("Set background color")
def set_background_color(self: _QtMainWidgetBase):
    """Set the background color of the selected cells."""
    qspreadsheet = _get_spreadsheet(self)
    index = _get_selected_column(qspreadsheet)
    qspreadsheet._set_background_colormap_with_dialog(index)
