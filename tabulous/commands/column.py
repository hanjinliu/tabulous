from __future__ import annotations
from typing import TYPE_CHECKING
from . import _utils, _dialogs

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase

_OPACITY_CONFIG = {
    "min": 0,
    "max": 1,
    "step": 0.01,
    "value": 0.8,
    "label": "opacity",
    "widget_type": "FloatSlider",
}

_BRIGHTNESS_CONFIG = {
    "min": -1,
    "max": 1,
    "step": 0.01,
    "value": 0.0,
    "label": "opacity",
    "widget_type": "FloatSlider",
}


def set_text_colormap(viewer: TableViewerBase) -> None:
    """Set text colormap to a column"""
    from tabulous._colormap import exec_colormap_dialog

    table, column_name = _utils.get_table_and_column_name(viewer)
    if cmap := exec_colormap_dialog(
        table.native._get_sub_frame(column_name),
        table.native,
    ):
        table.text_color.set(column_name, cmap, infer_parser=False)
    return None


def reset_text_colormap(viewer: TableViewerBase) -> None:
    """Reset text colormap"""
    table, column_name = _utils.get_table_and_column_name(viewer)
    del table.text_color[column_name]


def set_text_colormap_opacity(viewer: TableViewerBase) -> None:
    """Set opacity to the text colormap"""
    table, column_name = _utils.get_table_and_column_name(viewer)
    if val := _dialogs.get_value(x=_OPACITY_CONFIG, parent=viewer.native):
        table.text_color.set_opacity(column_name, val)


def invert_text_colormap(viewer: TableViewerBase) -> None:
    """Invert text colormap"""
    table, column_name = _utils.get_table_and_column_name(viewer)
    table.text_color.invert(column_name)


def adjust_brightness_text_colormap(viewer: TableViewerBase) -> None:
    """Adjust brightness of the text colormap"""
    table, column_name = _utils.get_table_and_column_name(viewer)
    if val := _dialogs.get_value(x=_BRIGHTNESS_CONFIG, parent=viewer.native):
        table.text_color.adjust_brightness(column_name, val)


def set_background_colormap(viewer: TableViewerBase) -> None:
    """Set background colormap to a column"""
    from tabulous._colormap import exec_colormap_dialog

    table, column_name = _utils.get_table_and_column_name(viewer)
    if cmap := exec_colormap_dialog(
        table.native._get_sub_frame(column_name),
        table.native,
    ):
        table.background_color.set(column_name, cmap, infer_parser=False)
    return None


def reset_background_colormap(viewer: TableViewerBase) -> None:
    """Reset background colormap"""
    table, column_name = _utils.get_table_and_column_name(viewer)
    del table.background_color[column_name]


def set_background_colormap_opacity(viewer: TableViewerBase) -> None:
    """Set opacity to the background colormap"""
    table, column_name = _utils.get_table_and_column_name(viewer)
    if val := _dialogs.get_value(x=_OPACITY_CONFIG, parent=viewer.native):
        table.background_color.set_opacity(column_name, val)


def invert_background_colormap(viewer: TableViewerBase) -> None:
    """Invert background colormap"""
    table, column_name = _utils.get_table_and_column_name(viewer)
    table.background_color.invert(column_name)


def adjust_brightness_background_colormap(viewer: TableViewerBase) -> None:
    """Adjust brightness of the background colormap"""
    table, column_name = _utils.get_table_and_column_name(viewer)
    if val := _dialogs.get_value(x=_BRIGHTNESS_CONFIG, parent=viewer.native):
        table.background_color.adjust_brightness(column_name, val)


def set_text_formatter(viewer: TableViewerBase) -> None:
    """Set text formatter"""
    from tabulous._text_formatter import exec_formatter_dialog

    table, column_name = _utils.get_table_and_column_name(viewer)

    if fmt := exec_formatter_dialog(
        table.native._get_sub_frame(column_name),
        table.native,
    ):
        table.formatter.set(column_name, fmt)
    return None


def reset_text_formatter(viewer: TableViewerBase) -> None:
    """Reset text formatter"""
    table, column_name = _utils.get_table_and_column_name(viewer)
    del table.formatter[column_name]
