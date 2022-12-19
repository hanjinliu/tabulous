from __future__ import annotations
from typing import TYPE_CHECKING
from . import _dialogs

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase


def activate_left(viewer: TableViewerBase):
    """Activate left table."""
    num = len(viewer.tables)
    if num == 0:
        return None
    src = viewer.current_index
    if src == 0:
        return None
    viewer.current_index = src - 1
    return viewer.native.setCellFocus()


def activate_right(viewer: TableViewerBase):
    """Activate right table."""
    num = len(viewer.tables)
    if num == 0:
        return None
    src = viewer.current_index
    if src == num - 1:
        return None
    viewer.current_index = src + 1
    return viewer.native.setCellFocus()


def swap_tab_with_left(viewer: TableViewerBase):
    """Swap the current tab with the left one"""
    num = len(viewer.tables)
    if num == 0:
        return None
    src = viewer.current_index
    if src == 0:
        return None
    viewer.tables.move(src, src - 1)


def swap_tab_with_right(viewer: TableViewerBase):
    """Swap the current tab with the right one"""
    num = len(viewer.tables)
    if num == 0:
        return None
    src = viewer.current_index
    if src == num - 1:
        return None
    viewer.tables.move(src + 1, src)


def tile_tables(viewer: TableViewerBase):
    """Tile tabs"""
    choices = [(table.name, idx) for idx, table in enumerate(viewer.tables)]
    out = _dialogs.choose_multiple(
        choices={"choices": choices, "widget_type": "Select"},
        parent=viewer.native,
    )
    if out:
        viewer.tables.tile(out)


def tile_with_adjacent_table(viewer: TableViewerBase):
    """Tile adjacent tabs"""
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
    """Untile current tab"""
    viewer.tables.untile(viewer.current_index)
