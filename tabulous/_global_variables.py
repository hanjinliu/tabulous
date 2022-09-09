from __future__ import annotations
from dataclasses import dataclass


class GlobalSetting:
    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


@dataclass
class TableSetting(GlobalSetting):
    """Default table settings."""

    max_row_count = 100000
    max_column_count = 100000
    font = "Arial"
    font_size = 10
    row_size = 28
    column_size = 100


@dataclass
class WindowSetting(GlobalSetting):
    ask_on_close = True


@dataclass
class ConsoleSetting(GlobalSetting):
    """Default name space for embedded console"""

    tabulous = "tbl"
    viewer = "viewer"
    pandas = "pd"
    numpy = "np"
    data = "DATA"


TABLE_SETTING = TableSetting()
WINDOW_SETTING = WindowSetting()
CONSOLE_SETTING = ConsoleSetting()


def get_table_setting() -> TableSetting:
    return TABLE_SETTING


def get_window_setting() -> WindowSetting:
    return WINDOW_SETTING


def get_console_setting() -> ConsoleSetting:
    return CONSOLE_SETTING
