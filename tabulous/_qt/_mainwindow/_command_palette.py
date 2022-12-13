from __future__ import annotations

from typing import TYPE_CHECKING
from qt_command_palette import get_palette

if TYPE_CHECKING:
    from ._base import _QtMainWidgetBase
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


@default_group.register("Show key map widget")
def show_keymap(self: _QtMainWidgetBase):
    """Show the widget to search for key bindings."""
    self.showKeyMap()


@default_group.register("Close window")
def close_window(self: _QtMainWidgetBase):
    """Close this window."""
    self.close()


@default_group.register("New window")
def new_window(self: _QtMainWidgetBase):
    """Create a new window."""
    viewer = self._table_viewer.__class__()
    return viewer._qwidget.activateWindow()


@default_group.register("Toggle toolbar visibility")
def toggle_toolbar(self: _QtMainWidgetBase):
    """Show or collapse the toolbar."""
    self.toggleToolBarVisibility()


@default_group.register("Toggle fullscreen")
def toggle_fullscreen(self: _QtMainWidgetBase):
    """Enable or disable fullscreen mode."""
    if self.isFullScreen():
        self.showNormal()
    else:
        self.showFullScreen()


@default_group.register("Undo")
def undo(self: _QtMainWidgetBase):
    """Undo last action."""
    self._table_viewer.current_table.undo_manager.undo()


@default_group.register("Redo")
def redo(self: _QtMainWidgetBase):
    """Redo last undone action."""
    self._table_viewer.current_table.undo_manager.redo()


@file_group.register("Open a file as a table")
def open_table(self: _QtMainWidgetBase):
    """Select a file in the file dialog and open it as a Table."""
    self._toolbar.open_table()


@file_group.register("Open a file as a spreadsheet")
def open_spreadsheet(self: _QtMainWidgetBase):
    """Select a file in the file dialog and open it as a Spreadsheet."""
    self._toolbar.open_spreadsheet()


@file_group.register("Save current table/spreadsheet")
def save_table(self: _QtMainWidgetBase):
    """Save the current table or spreadsheet as a file."""
    self._toolbar.save_table()


@file_group.register("Open sample data")
def open_sample(self: _QtMainWidgetBase):
    """Open a seaborn sample data as a Table."""
    self._toolbar.open_sample()


@table_group.register("Copy current table as a new Table")
def copy_as_table(self: _QtMainWidgetBase):
    """Copy the data of the current table as a new Table."""
    self._toolbar.copy_as_table()


@table_group.register("Copy current table as a new Spreadsheet")
def copy_as_spreadsheet(self: _QtMainWidgetBase):
    """Copy the data of the current table as a new Spreadsheet."""
    self._toolbar.copy_as_spreadsheet()


@table_group.register("Group by")
def groupby(self: _QtMainWidgetBase):
    """Run groupby function on the current table by arbitrary columns."""
    self._toolbar.groupby()


@table_group.register("Switch header and the top row")
def switch_header(self: _QtMainWidgetBase):
    """Convert the top row to header or vice versa."""
    self._toolbar.switch_header()


@table_group.register("Concatenate tables")
def concat(self: _QtMainWidgetBase):
    """Concatenate multiple tables into one table."""
    self._toolbar.concat()


@table_group.register("Pivot table")
def pivot(self: _QtMainWidgetBase):
    """Pivot the current table."""
    self._toolbar.pivot()


@table_group.register("Melt table")
def melt(self: _QtMainWidgetBase):
    """Melt the current table."""
    self._toolbar.melt()


@table_group.register("Find item")
def find_item(self: _QtMainWidgetBase):
    """Open the finder widget to find table items by its text or value."""
    self._toolbar.find_item()


@table_group.register("Sort table")
def sort_table(self: _QtMainWidgetBase):
    """Sort the current table by arbitrary columns."""
    self._toolbar.sort_table()


@table_group.register("Generate random values")
def random(self: _QtMainWidgetBase):
    """Open the random value generator widget."""
    self._toolbar.random()


@analysis_group.register("Summarize table")
def summarize_table(self: _QtMainWidgetBase):
    """Summarize the current table by mean, std, etc."""
    self._toolbar.summarize_table()


@analysis_group.register("Evaluate expression")
def eval(self: _QtMainWidgetBase):
    """Evaluate an expression on the current table."""
    self._toolbar.eval()


@analysis_group.register("Filter table")
def filter(self: _QtMainWidgetBase):
    """Filter the current table by arbitrary conditions."""
    self._toolbar.filter()


@analysis_group.register("Open optimizer widget")
def optimize(self: _QtMainWidgetBase):
    """Open the optimizer widget to run scipy.minimize on the table."""
    self._toolbar.optimize()


@analysis_group.register("Open statistics test widget")
def stats_test(self: _QtMainWidgetBase):
    """Open the statistics test widget to run scipy.stats tests."""
    self._toolbar.stats_test()


@analysis_group.register("Open scikit-learn widget")
def sklearn_analysis(self: _QtMainWidgetBase):
    """Open the scikit-learn widget to run clustering, decomposition, etc."""
    self._toolbar.sklearn_analysis()


@analysis_group.register("Toggle QtConsole")
def toggle_console(self: _QtMainWidgetBase):
    """Show or hide the console widget visibility."""
    self._toolbar.toggle_console()


@view_group.register("Popup table")
def view_popup(self: _QtMainWidgetBase):
    """View the current table in a popup window."""
    self._toolbar.change_view_mode("popup")


@view_group.register("Split table horizontally")
def view_horizontal(self: _QtMainWidgetBase):
    """Split the current table horizontally."""
    self._toolbar.change_view_mode("horizontal")


@view_group.register("Split table vertically")
def view_vertical(self: _QtMainWidgetBase):
    """Split the current table vertically."""
    self._toolbar.change_view_mode("vertical")


@view_group.register("Reset view")
def view_normal(self: _QtMainWidgetBase):
    """Reset the view mode of the current table."""
    self._toolbar.change_view_mode("normal")


@plot_group.register("Run plt.plot")
def plot(self: _QtMainWidgetBase):
    """Open a dialog to run plt.plot."""
    self._toolbar.plot()


@plot_group.register("Run plt.scatter")
def scatter(self: _QtMainWidgetBase):
    """Open a dialog to run plt.scatter."""
    self._toolbar.scatter()


@plot_group.register("Run plt.errorbar")
def errorbar(self: _QtMainWidgetBase):
    """Open a dialog to run plt.errorbar."""
    self._toolbar.errorbar()


@plot_group.register("Run plt.hist")
def hist(self: _QtMainWidgetBase):
    """Open a dialog to run plt.hist."""
    self._toolbar.hist()


@plot_group.register("Run sns.swarmplot")
def swarmplot(self: _QtMainWidgetBase):
    """Open a dialog to run sns.swarmplot."""
    self._toolbar.swarmplot()


@plot_group.register("Run sns.barplot")
def barplot(self: _QtMainWidgetBase):
    """Open a dialog to run sns.barplot."""
    self._toolbar.barplot()


@plot_group.register("Run sns.boxplot")
def boxplot(self: _QtMainWidgetBase):
    """Open a dialog to run sns.boxplot."""
    self._toolbar.boxplot()


@plot_group.register("Run sns.boxenplot")
def boxenplot(self: _QtMainWidgetBase):
    """Open a dialog to run sns.boxenplot."""
    self._toolbar.boxenplot()


@plot_group.register("Create a new figure canvas")
def new_figure(self: _QtMainWidgetBase):
    """Create a new figure canvas in the side area."""
    self._toolbar.new_figure()


@selection_group.register("Copy cells")
def copy(self: _QtMainWidgetBase):
    """Copy the selected cells to the clipboard as tab-separated text."""
    self._table_viewer.copy_data()


@selection_group.register("Copy cells with headers")
def copy_with_header(self: _QtMainWidgetBase):
    """Copy the selected cells and headers to the clipboard as tab-separated text."""
    self._table_viewer.copy_data(header=True)


@selection_group.register("Copy as a new Table")
def copy_as_new_table(self: _QtMainWidgetBase):
    """Copy the selected cells and create a new table."""
    self._table_viewer.current_table._qwidget._copy_as_new_table("table")


@selection_group.register("Copy as a new SpreadSheet")
def copy_as_new_spreadsheet(self: _QtMainWidgetBase):
    """Copy the selected cells and create a new spreadsheet."""
    self._table_viewer.current_table._qwidget._copy_as_new_table("spreadsheet")


@selection_group.register("Copy as tab separated text")
def copy_as_tab(self: _QtMainWidgetBase):
    """Copy the selected cells to the clipboard as tab-separated text."""
    self._table_viewer.current_table._qwidget.copyToClipboard(headers=False, sep="\t")


@selection_group.register("Copy as tab separated text with headers")
def copy_as_tab_with_header(self: _QtMainWidgetBase):
    """Copy the selected cells and headers to the clipboard as tab-separated text."""
    self._table_viewer.current_table._qwidget.copyToClipboard(headers=True, sep="\t")


@selection_group.register("Copy as comma separated text")
def copy_as_comma(self: _QtMainWidgetBase):
    """Copy the selected cells to the clipboard as comma-separated text."""
    self._table_viewer.current_table._qwidget.copyToClipboard(headers=False, sep=",")


@selection_group.register("Copy as comma separated text with headers")
def copy_as_comma_with_header(self: _QtMainWidgetBase):
    """Copy the selected cells and headers to the clipboard as comma-separated text."""
    self._table_viewer.current_table._qwidget.copyToClipboard(headers=True, sep=",")


@selection_group.register("Copy as literal")
def copy_as_literal(self: _QtMainWidgetBase):
    """Copy the selected cells as a python literal for use in the console."""
    self._table_viewer.current_table._qwidget._copy_as_literal()


@selection_group.register("Paste from comma separated text")
def paste_from_comma(self: _QtMainWidgetBase):
    """Paste comma-separated text from the clipboard at the selection."""
    self._table_viewer.current_table._qwidget.pasteFromClipBoard(sep=",")


@selection_group.register("Paste from numpy-style text")
def paste_from_numpy(self: _QtMainWidgetBase):
    """Paste numpy-style text from the clipboard at the selection."""
    self._table_viewer.current_table._qwidget._paste_numpy_str()


@selection_group.register("Add highlight")
def add_highlight(self: _QtMainWidgetBase):
    """Add highlight at the selection."""
    qwidget = self._table_viewer.current_table._qwidget
    qwidget.setHighlights(qwidget.highlights() + qwidget.selections())


@selection_group.register("Select all")
def select_all(self: _QtMainWidgetBase):
    """Select all the cells in the table."""
    self._table_viewer.current_table._qwidget._qtable_view.selectAll()


@selection_group.register("Cut selected cells")
def cut(self: _QtMainWidgetBase):
    """Cut the selected cells to the clipboard as tab-separated text."""
    qwidget = self._table_viewer.current_table._qwidget
    qwidget.copyToClipboard(headers=False)
    return qwidget.deleteValues()


@selection_group.register("Paste data")
def paste(self: _QtMainWidgetBase):
    """Paste data from the clipboard at the selection."""
    self._table_viewer.paste_data()


@selection_group.register("Delete selected cells")
def delete(self: _QtMainWidgetBase):
    """Delete the selected cells."""
    self._table_viewer.current_table._qwidget.deleteValues()


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
