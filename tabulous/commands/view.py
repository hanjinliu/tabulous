from __future__ import annotations

from typing import TYPE_CHECKING
from . import _dialogs, _utils

if TYPE_CHECKING:
    from tabulous.widgets import TableBase, TableViewerBase


def set_popup_mode(viewer: TableViewerBase):
    """Change current table to popup mode."""
    table = _utils.get_table(viewer)
    table.view_mode = "popup"


def set_dual_v_mode(viewer: TableViewerBase):
    """Change current table to vertical dual mode."""
    table = _utils.get_table(viewer)
    table.view_mode = "vertical"


def set_dual_h_mode(viewer: TableViewerBase):
    """Change current table to horizontal dual mode."""
    table = _utils.get_table(viewer)
    table.view_mode = "horizontal"


def reset_view_mode(viewer: TableViewerBase):
    """Change current table to the normal mode."""
    table = _utils.get_table(viewer)
    table.view_mode = "normal"
