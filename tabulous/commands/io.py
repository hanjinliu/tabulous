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
    """Open a file as a table."""
    return viewer._qwidget.openFromDialog(type="table")


def open_spreadsheet(viewer: TableViewerBase):
    """Open a file as a spreadsheet."""
    return viewer._qwidget.openFromDialog(type="spreadsheet")


def save_table(viewer: TableViewerBase):
    """Save current table."""
    return viewer._qwidget.saveFromDialog()


def open_sample(viewer: TableViewerBase):
    """Open a seaborn sample data."""
    out = choose_one(choice={"choices": SAMPLE_CHOICES, "nullable": False})
    if out is not None:
        viewer.open_sample(out)
