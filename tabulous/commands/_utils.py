from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tabulous.widgets import TableBase, TableViewerBase, Table, SpreadSheet


def get_table(viewer: TableViewerBase) -> TableBase:
    """Safely get the current table of the given viewer."""
    if table := viewer.current_table:
        return table
    raise ValueError("No table found in the viewer.")


def get_mutable_table(viewer: TableViewerBase) -> Table | SpreadSheet:
    """Safely get the current mutable-type table of the given viewer."""
    table = get_table(viewer)
    if table.table_type in ("Table", "SpreadSheet"):
        return table
    from tabulous.exceptions import TableImmutableError

    raise TableImmutableError(f"Table {table.name!r} is immutable.")


def get_spreadsheet(viewer: TableViewerBase) -> SpreadSheet:
    """Safely get the current mutable-type table of the given viewer."""
    table = get_table(viewer)
    if table.table_type == "SpreadSheet":
        return table

    raise TypeError(f"Table {table.name!r} is not a spreadsheet.")


def get_selected_row(viewer: TableViewerBase) -> int:
    table = get_table(viewer)
    selected = table.index.selected
    if len(selected) == 0:
        raise ValueError("No index selected")
    if len(selected) > 1:
        raise ValueError("Multiple indices selected")

    return selected[0].start


def get_selected_column(viewer: TableViewerBase) -> int:
    table = get_table(viewer)
    selected = table.columns.selected
    if len(selected) == 0:
        raise ValueError("No columns selected")
    if len(selected) > 1:
        raise ValueError("Multiple columns selected")

    return selected[0].start
