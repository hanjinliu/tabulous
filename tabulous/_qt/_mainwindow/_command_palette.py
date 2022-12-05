from __future__ import annotations

from typing import TYPE_CHECKING
from qt_command_palette import get_palette

if TYPE_CHECKING:
    from ._base import _QtMainWidgetBase

palette = get_palette("tabulous")

default_group = palette.add_group("")
file_group = palette.add_group("File")
table_group = palette.add_group("Table")
analysis_group = palette.add_group("Analysis")
view_group = palette.add_group("View")
plot_group = palette.add_group("Plot")
selection_group = palette.add_group("Selection")


@default_group.register("Show key map")
def show_keymap(self: _QtMainWidgetBase):
    self.showKeyMap()


@default_group.register("Close window")
def close_window(self: _QtMainWidgetBase):
    self.close()


@default_group.register("New window")
def new_window(self: _QtMainWidgetBase):
    viewer = self._table_viewer.__class__()
    return viewer._qwidget.activateWindow()


@default_group.register("Toggle toolbar visibility")
def toggle_toolbar(self: _QtMainWidgetBase):
    self.toggleToolBarVisibility()


@default_group.register("Toggle fullscreen")
def toggle_fullscreen(self: _QtMainWidgetBase):
    if self.isFullScreen():
        self.showNormal()
    else:
        self.showFullScreen()


@default_group.register("Undo")
def undo(self: _QtMainWidgetBase):
    self._table_viewer.current_table.undo_manager.undo()


@default_group.register("Redo")
def redo(self: _QtMainWidgetBase):
    self._table_viewer.current_table.undo_manager.redo()


@file_group.register("Open a file as a table")
def open_table(self: _QtMainWidgetBase):
    self._toolbar.open_table()


@file_group.register("Open a file as a spreadsheet")
def open_spreadsheet(self: _QtMainWidgetBase):
    self._toolbar.open_spreadsheet()


@file_group.register("Save current table/spreadsheet")
def save_table(self: _QtMainWidgetBase):
    self._toolbar.save_table()


@file_group.register("Open sample data")
def open_sample(self: _QtMainWidgetBase):
    self._toolbar.open_sample()


@table_group.register("Copy current table as a new Table")
def copy_as_table(self: _QtMainWidgetBase):
    self._toolbar.copy_as_table()


@table_group.register("Copy current table as a new Spreadsheet")
def copy_as_spreadsheet(self: _QtMainWidgetBase):
    self._toolbar.copy_as_spreadsheet()


@table_group.register("Group by")
def groupby(self: _QtMainWidgetBase):
    self._toolbar.groupby()


@table_group.register("Switch header and the top row")
def switch_header(self: _QtMainWidgetBase):
    self._toolbar.switch_header()


@table_group.register("Concatenate tables")
def concat(self: _QtMainWidgetBase):
    self._toolbar.concat()


@table_group.register("Pivot table")
def pivot(self: _QtMainWidgetBase):
    self._toolbar.pivot()


@table_group.register("Melt table")
def melt(self: _QtMainWidgetBase):
    self._toolbar.melt()


@table_group.register("Find item")
def find_item(self: _QtMainWidgetBase):
    self._toolbar.find_item()


@table_group.register("Sort table")
def sort_table(self: _QtMainWidgetBase):
    self._toolbar.sort_table()


@table_group.register("Generate random values")
def random(self: _QtMainWidgetBase):
    self._toolbar.random()


@analysis_group.register("Summarize table")
def summarize_table(self: _QtMainWidgetBase):
    self._toolbar.summarize_table()


@analysis_group.register("Evaluate expression")
def eval(self: _QtMainWidgetBase):
    self._toolbar.eval()


@analysis_group.register("Filter table")
def filter(self: _QtMainWidgetBase):
    self._toolbar.filter()


@analysis_group.register("Open optimizer widget")
def optimize(self: _QtMainWidgetBase):
    self._toolbar.optimize()


@analysis_group.register("Open statistics test widget")
def stats_test(self: _QtMainWidgetBase):
    self._toolbar.stats_test()


@analysis_group.register("Open scikit-learn widget")
def sklearn_analysis(self: _QtMainWidgetBase):
    self._toolbar.sklearn_analysis()


@analysis_group.register("Toggle QtConsole")
def toggle_console(self: _QtMainWidgetBase):
    self._toolbar.toggle_console()


@view_group.register("Popup table")
def view_popup(self: _QtMainWidgetBase):
    self._toolbar.change_view_mode("popup")


@view_group.register("Split table horizontally")
def view_horizontal(self: _QtMainWidgetBase):
    self._toolbar.change_view_mode("horizontal")


@view_group.register("Split table vertically")
def view_vertical(self: _QtMainWidgetBase):
    self._toolbar.change_view_mode("vertical")


@view_group.register("Reset view")
def view_normal(self: _QtMainWidgetBase):
    self._toolbar.change_view_mode("normal")


@plot_group.register("Run plt.plot")
def plot(self: _QtMainWidgetBase):
    self._toolbar.plot()


@plot_group.register("Run plt.scatter")
def scatter(self: _QtMainWidgetBase):
    self._toolbar.scatter()


@plot_group.register("Run plt.errorbar")
def errorbar(self: _QtMainWidgetBase):
    self._toolbar.errorbar()


@plot_group.register("Run plt.hist")
def hist(self: _QtMainWidgetBase):
    self._toolbar.hist()


@plot_group.register("Run sns.swarmplot")
def swarmplot(self: _QtMainWidgetBase):
    self._toolbar.swarmplot()


@plot_group.register("Run sns.barplot")
def barplot(self: _QtMainWidgetBase):
    self._toolbar.barplot()


@plot_group.register("Run sns.boxplot")
def boxplot(self: _QtMainWidgetBase):
    self._toolbar.boxplot()


@plot_group.register("Run sns.boxenplot")
def boxenplot(self: _QtMainWidgetBase):
    self._toolbar.boxenplot()


@plot_group.register("Create a new figure canvas")
def new_figure(self: _QtMainWidgetBase):
    self._toolbar.new_figure()


@selection_group.register("Copy cells")
def copy(self: _QtMainWidgetBase):
    self._table_viewer.copy_data()


@selection_group.register("Copy cells with headers")
def copy_with_header(self: _QtMainWidgetBase):
    self._table_viewer.copy_data(header=True)


@selection_group.register("Copy as a new Table")
def copy_as_new_table(self: _QtMainWidgetBase):
    self._table_viewer.current_table._qwidget._copy_as_new_table("table")


@selection_group.register("Copy as a new SpreadSheet")
def copy_as_new_spreadsheet(self: _QtMainWidgetBase):
    self._table_viewer.current_table._qwidget._copy_as_new_table("spreadsheet")


@selection_group.register("Copy as tab separated text")
def copy_as_tab(self: _QtMainWidgetBase):
    self._table_viewer.current_table._qwidget.copyToClipboard(headers=False, sep="\t")


@selection_group.register("Copy as tab separated text with headers")
def copy_as_tab_with_header(self: _QtMainWidgetBase):
    self._table_viewer.current_table._qwidget.copyToClipboard(headers=True, sep="\t")


@selection_group.register("Copy as comma separated text")
def copy_as_comma(self: _QtMainWidgetBase):
    self._table_viewer.current_table._qwidget.copyToClipboard(headers=False, sep=",")


@selection_group.register("Copy as comma separated text with headers")
def copy_as_comma_with_header(self: _QtMainWidgetBase):
    self._table_viewer.current_table._qwidget.copyToClipboard(headers=True, sep=",")


@selection_group.register("Copy as literal")
def copy_as_literal(self: _QtMainWidgetBase):
    self._table_viewer.current_table._qwidget._copy_as_literal()


@selection_group.register("Paste from comma separated text")
def paste_from_comma(self: _QtMainWidgetBase):
    self._table_viewer.current_table._qwidget.pasteFromClipBoard(sep=",")


@selection_group.register("Paste from numpy-style text")
def paste_from_numpy(self: _QtMainWidgetBase):
    self._table_viewer.current_table._qwidget._paste_numpy_str()


@selection_group.register("Add highlight")
def add_highlight(self: _QtMainWidgetBase):
    qwidget = self._table_viewer.current_table._qwidget
    qwidget.setHighlights(qwidget.highlights() + qwidget.selections())


@selection_group.register("Select all")
def select_all(self: _QtMainWidgetBase):
    self._table_viewer.current_table._qwidget._qtable_view.selectAll()


@selection_group.register("Cut selected cells")
def cut(self: _QtMainWidgetBase):
    qwidget = self._table_viewer.current_table._qwidget
    qwidget.copyToClipboard(headers=False)
    return qwidget.deleteValues()


@selection_group.register("Paste cells")
def paste(self: _QtMainWidgetBase):
    self._table_viewer.paste_data()


@selection_group.register("Delete selected cells")
def delete(self: _QtMainWidgetBase):
    self._table_viewer.current_table._qwidget.deleteValues()
