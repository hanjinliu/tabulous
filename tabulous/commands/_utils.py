from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tabulous.widgets import TableBase, TableViewerBase, Table, SpreadSheet


def get_table(viewer: TableViewerBase) -> TableBase:
    if table := viewer.current_table:
        return table
    raise ValueError("No table found in the viewer.")


def get_mutable_table(viewer: TableViewerBase) -> Table | SpreadSheet:
    table = get_table(viewer)
    if table.table_type in ("Table", "SpreadSheet"):
        return table
    from tabulous.exceptions import TableImmutableError

    raise TableImmutableError(f"Table {table.name!r} is immutable.")
