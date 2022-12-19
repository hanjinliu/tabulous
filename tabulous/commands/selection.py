from __future__ import annotations
from typing import TYPE_CHECKING
from . import _dialogs, _utils

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase


def copy_data_tab_separated(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget.copyToClipboard(headers=False, sep="\t")


def copy_data_with_header_tab_separated(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget.copyToClipboard(headers=True, sep="\t")


def copy_data_comma_separated(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget.copyToClipboard(headers=False, sep=",")


def copy_data_with_header_comma_separated(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget.copyToClipboard(headers=True, sep=",")


def copy_as_literal(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget._copy_as_literal()


def copy_as_new_table(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget._copy_as_new_table(type_="table")


def copy_as_new_spreadsheet(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget._copy_as_new_table(type_="spreadsheet")


def select_all(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget._qtable_view.selectAll()


def cut_data(viewer: TableViewerBase):
    qtable = _utils.get_mutable_table(viewer)._qwidget
    qtable.copyToClipboard(headers=False)
    qtable.deleteValues()


def paste_data_tab_separated(viewer: TableViewerBase):
    _utils.get_mutable_table(viewer)._qwidget.pasteFromClipBoard(sep="\t")


def paste_data_comma_separated(viewer: TableViewerBase):
    _utils.get_mutable_table(viewer)._qwidget.pasteFromClipBoard(sep=",")


def paste_data_from_numpy_string(viewer: TableViewerBase):
    _utils.get_mutable_table(viewer)._qwidget._paste_numpy_str()


def delete_values(viewer: TableViewerBase):
    _utils.get_mutable_table(viewer)._qwidget.deleteValues()


def add_highlight(viewer: TableViewerBase):
    qwidget = _utils.get_table(viewer)._qwidget
    qwidget.setHighlights(qwidget.highlights() + qwidget.selections())


def show_traceback_at_error(viewer: TableViewerBase):
    qtable_view = _utils.get_mutable_table(viewer)._qwidget._qtable_view
    idx = qtable_view._selection_model.current_index
    if slot := qtable_view._table_map.get_by_dest(idx, None):
        if slot._current_error is not None:
            slot.raise_in_msgbox()


def show_context_menu(viewer: TableViewerBase):
    qtable = _utils.get_table(viewer)._qwidget
    r, c = qtable._qtable_view._selection_model.current_index
    if r >= 0 and c >= 0:
        index = qtable._qtable_view.model().index(r, c)
        rect = qtable._qtable_view.visualRect(index)
        qtable.showContextMenu(rect.center())
    elif r < 0:
        header = qtable._qtable_view.horizontalHeader()
        rect = header.visualRectAtIndex(c)
        header._show_context_menu(rect.center())
    elif c < 0:
        header = qtable._qtable_view.verticalHeader()
        rect = header.visualRectAtIndex(r)
        header._show_context_menu(rect.center())
    else:
        raise RuntimeError("Invalid index")


def notify_editability(viewer: TableViewerBase):
    viewer._qwidget._tablestack.notifyEditability()


def set_column_dtype(viewer: TableViewerBase):
    """Set column specific dtype for data conversion and validation."""
    from tabulous._qt._table._dtype import QDtypeWidget

    sheet = _utils.get_spreadsheet(viewer)._qwidget
    col = _utils.get_selected_column(viewer)
    if out := QDtypeWidget.requestValue(viewer._qwidget):
        dtype_str, validation, formatting = out
        if dtype_str == "unset":
            dtype_str = None
        colname = sheet._data_raw.columns[col]
        sheet.setColumnDtype(colname, dtype_str)
        if validation:
            sheet._set_default_data_validator(colname)
        if formatting:
            sheet._set_default_text_formatter(colname)
    return None


def insert_row_above(viewer: TableViewerBase):
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return notify_editability()
    row, _ = sheet._qtable_view._selection_model.current_index
    return sheet.insertRows(row, 1)


def insert_row_below(viewer: TableViewerBase):
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return notify_editability()
    row, _ = sheet._qtable_view._selection_model.current_index
    return sheet.insertRows(row + 1, 1)


def insert_column_left(viewer: TableViewerBase):
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return notify_editability()
    _, col = sheet._qtable_view._selection_model.current_index
    return sheet.insertColumns(col, 1)


def insert_column_right(viewer: TableViewerBase):
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return notify_editability()
    _, col = sheet._qtable_view._selection_model.current_index
    return sheet.insertColumns(col + 1, 1)


def remove_this_row(viewer: TableViewerBase):
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return notify_editability()
    row, _ = sheet._qtable_view._selection_model.current_index
    return sheet.removeRows(row, 1)


def remove_this_column(viewer: TableViewerBase):
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return notify_editability()
    _, col = sheet._qtable_view._selection_model.current_index
    return sheet.removeColumns(col, 1)


def remove_selected_rows(viewer: TableViewerBase):
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return notify_editability()
    row, _ = sheet._qtable_view._selection_model.current_index
    _, rng = sheet._qtable_view._selection_model.range_under_index(row, 0)
    if rng is not None:
        row_range = rng[0]
        sheet.removeRows(row_range.start, row_range.stop - row_range.start)
    return None


def remove_selected_columns(viewer: TableViewerBase):
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return notify_editability()
    _, col = sheet._qtable_view._selection_model.current_index
    _, rng = sheet._qtable_view._selection_model.range_under_index(0, col)
    if rng is not None:
        col_range = rng[1]
        sheet.removeColumns(col_range.start, col_range.stop - col_range.start)
    return None


def set_foreground_colormap(viewer: TableViewerBase) -> None:
    """Set the foreground colormap from a GUI dialog."""
    from tabulous._qt._table._base._colormap import exec_colormap_dialog

    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)

    column_name = sheet._filtered_columns[index]
    if cmap := exec_colormap_dialog(sheet.getDataFrame()[column_name], sheet):
        sheet.setForegroundColormap(column_name, cmap)
    return None


def reset_foreground_colormap(viewer: TableViewerBase) -> None:
    """Reset the foreground colormap at given index."""
    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)
    column_name = sheet._filtered_columns[index]
    return sheet.setForegroundColormap(column_name, None)


def set_background_colormap(viewer: TableViewerBase) -> None:
    """Set the background colormap from a GUI dialog."""
    from tabulous._qt._table._base._colormap import exec_colormap_dialog

    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)
    column_name = sheet._filtered_columns[index]
    if cmap := exec_colormap_dialog(sheet.getDataFrame()[column_name], sheet):
        sheet.setBackgroundColormap(column_name, cmap)
    return None


def reset_background_colormap(viewer: TableViewerBase) -> None:
    """Reset the background colormap at given index."""
    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)
    column_name = sheet._filtered_columns[index]
    return sheet.setBackgroundColormap(column_name, None)


def set_text_formatter(viewer: TableViewerBase) -> None:
    """Set the text formatter at given index."""
    from tabulous._qt._table._base._text_formatter import exec_formatter_dialog

    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)
    column_name = sheet._filtered_columns[index]

    if fmt := exec_formatter_dialog(sheet.getDataFrame()[column_name], sheet):
        sheet.setTextFormatter(column_name, fmt)
    return None


def reset_text_formatter(viewer: TableViewerBase) -> None:
    """Reset the text formatter at given index."""
    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)
    column_name = sheet._filtered_columns[index]
    return sheet.setTextFormatter(column_name, None)
