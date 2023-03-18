from __future__ import annotations
from typing import TYPE_CHECKING
from qt_command_palette import get_storage

if TYPE_CHECKING:
    from tabulous._qt._mainwindow import _QtMainWidgetBase


def register_storage_vars():
    storage = get_storage("tabulous")

    @storage.mark_getter
    def viewer(self: _QtMainWidgetBase):
        return self._table_viewer

    @storage.mark_getter
    def table(self: _QtMainWidgetBase):
        return self._table_viewer.current_table
