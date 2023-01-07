from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tabulous.widgets import TableBase, TableViewerBase, Table, SpreadSheet

__void = object()


def get_table(viewer: TableViewerBase, default=__void) -> TableBase:
    """Safely get the current table of the given viewer."""
    if table := viewer.current_table:
        return table
    if default is not __void:
        return default
    raise ValueError("No table found in the viewer.")


def get_mutable_table(viewer: TableViewerBase, default=__void) -> Table | SpreadSheet:
    """Safely get the current mutable-type table of the given viewer."""
    try:
        table = get_table(viewer)
    except ValueError as e:
        if default is not __void:
            return default
        raise e

    if table.table_type in ("Table", "SpreadSheet"):
        return table

    if default is not __void:
        return default
    from tabulous.exceptions import TableImmutableError

    raise TableImmutableError(f"Table {table.name!r} is immutable.")


def get_spreadsheet(viewer: TableViewerBase, default=__void) -> SpreadSheet:
    """Safely get the current mutable-type table of the given viewer."""
    try:
        table = get_table(viewer)
    except ValueError as e:
        if default is not __void:
            return default
        raise e
    if table.table_type == "SpreadSheet":
        return table
    if default is not __void:
        return default
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
        raise ValueError("Multiple ranges are selected")
    first = selected[0]
    if first.stop != first.start + 1:
        raise ValueError("Multiple columns are selected")

    return first.start


def get_table_and_column_name(viewer: TableViewerBase) -> tuple[TableBase, str]:
    table = get_table(viewer)
    selected = table.columns.selected
    if len(selected) == 0:
        raise ValueError("No columns selected")
    if len(selected) > 1:
        raise ValueError("Multiple ranges are selected")
    first = selected[0]
    if first.stop != first.start + 1:
        raise ValueError("Multiple columns are selected")

    return table, table.columns[first.start]


def get_selected_columns(
    viewer: TableViewerBase, assert_exists: bool = True
) -> list[int]:
    table = get_table(viewer)
    selected = table.columns.selected
    if assert_exists and len(selected) == 0:
        raise ValueError("No columns selected")

    out: list[int] = []
    for sl in selected:
        out.extend(range(sl.start, sl.stop))
    return out


def get_a_selection(table: TableBase) -> tuple[slice, slice]:
    """Get a selection of the given table."""
    sels = table.selections
    if len(sels) != 1:
        raise ValueError("Multiple selections are selected")
    return sels[0]


def get_clipboard_text() -> str:
    from qtpy import QtWidgets as QtW

    s = QtW.QApplication.clipboard().text()
    if s:
        return s
    raise ValueError("No text found in clipboard.")
