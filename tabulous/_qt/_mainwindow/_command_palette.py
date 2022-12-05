from __future__ import annotations

from typing import TYPE_CHECKING
from qt_command_palette import get_palette

if TYPE_CHECKING:
    from ._base import _QtMainWidgetBase

palette = get_palette("tabulous")

file_group = palette.add_group("File")
table_group = palette.add_group("Table")
analysis_group = palette.add_group("Analysis")
view_group = palette.add_group("View")
plot_group = palette.add_group("Plot")


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


@table_group.register("Copy as table")
def copy_as_table(self: _QtMainWidgetBase):
    self._toolbar.copy_as_table()


@table_group.register("Copy as spreadsheet")
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
