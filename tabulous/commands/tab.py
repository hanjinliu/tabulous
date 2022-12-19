from __future__ import annotations
from typing import TYPE_CHECKING
from . import _dialogs, _utils

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase


def _get_src(viewer: TableViewerBase) -> int | None:
    num = len(viewer.tables)
    if num == 0:
        return None
    src = viewer.current_index
    if src == num - 1:
        return None
    return src


def activate_left(viewer: TableViewerBase):
    """Activate the left table."""
    src = _get_src(viewer)
    if src is not None:
        viewer.current_index = src - 1
        return viewer.native.setCellFocus()


def activate_right(viewer: TableViewerBase):
    """Activate the next table."""
    src = _get_src(viewer)
    if src is not None:
        viewer.current_index = src + 1
        return viewer.native.setCellFocus()


def swap_tab_with_left(viewer: TableViewerBase):
    """Swap the current table with the left one."""
    src = _get_src(viewer)
    if src is not None:
        viewer.tables.move(src, src - 1)


def swap_tab_with_right(viewer: TableViewerBase):
    """Swap the current table with the right one."""
    src = _get_src(viewer)
    if src is not None:
        viewer.tables.move(src + 1, src)


def tile_tables(viewer: TableViewerBase):
    """Open a dialog to choose tables to be tiled."""
    choices = [(table.name, idx) for idx, table in enumerate(viewer.tables)]
    out = _dialogs.choose_multiple(
        choices={"choices": choices, "widget_type": "Select"}
    )
    if out:
        viewer.tables.tile(out)


def tile_with_adjacent_table(viewer: TableViewerBase):
    """Tile current table with next (or previous) one."""
    num = len(viewer.tables)
    if num < 2:
        return None
    idx = viewer.current_index
    if idx < num - 1:
        indices = [idx, idx + 1]
    else:
        indices = [idx - 1, idx]
    all_indices = []
    for i in indices:
        all_indices.extend(viewer.native._tablestack.tiledIndices(i))

    all_indices = list(set(all_indices))
    return viewer.tables.tile(all_indices, orientation="horizontal")


def untile_table(viewer: TableViewerBase):
    """Untile currently selected table."""
    viewer.tables.untile(viewer.current_index)
