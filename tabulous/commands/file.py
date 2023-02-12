from __future__ import annotations
from typing import TYPE_CHECKING
from ._dialogs import choose_one

if TYPE_CHECKING:
    from tabulous.widgets._mainwindow import TableViewerBase

__all__ = ["open_table", "open_spreadsheet", "save_table", "open_sample"]

# fmt: off
SAMPLE_CHOICES = [
    "anagrams", "anscombe", "attention", "brain_networks", "car_crashes", "diamonds",
    "dots", "dowjones", "exercise", "flights", "fmri", "geyser", "glue", "healthexp",
    "iris", "mpg", "penguins", "planets", "seaice", "taxis", "tips", "titanic",
]
# fmt: on


def open_table(viewer: TableViewerBase):
    """Open a file as a table"""
    paths = viewer.history_manager.openFileDialog(mode="rm", caption="Open file(s)")
    for path in paths:
        viewer.open(path, type="table")
    return None


def open_spreadsheet(viewer: TableViewerBase):
    """Open a file as a spreadsheet"""
    paths = viewer.history_manager.openFileDialog(mode="rm", caption="Open file(s)")
    for path in paths:
        viewer.open(path, type="spreadsheet")
    return None


def save_table(viewer: TableViewerBase):
    """Save current table data"""
    if table := viewer.current_table:
        path = viewer.history_manager.openFileDialog(mode="w", caption="Save table")
        if path:
            table.save(path)
    return None


def save_table_to_source(viewer: TableViewerBase):
    """Save current table data to the source file if exists"""
    if table := viewer.current_table:
        if path := table.source.path:
            table.save(path)
        else:
            save_table(viewer)
    return None


def open_sample(viewer: TableViewerBase):
    """Open sample data"""
    out = choose_one(choice={"choices": SAMPLE_CHOICES, "nullable": False})
    if out is not None:
        viewer.open_sample(out)


def save_as_xlsx(viewer: TableViewerBase):
    """Save all tables to an Excel book"""
    path = viewer.history_manager.openFileDialog(
        mode="w", caption="Save table", filter="Excel book (*.xlsx; *.xls)"
    )
    if path:
        viewer.save_all(path)
    return None
