from __future__ import annotations
from typing import TYPE_CHECKING
from . import _dialogs, _utils

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase


def new_spreadsheet(viewer: TableViewerBase):
    """Add an empty spreadsheet."""
    viewer.add_spreadsheet()


def copy_as_table(viewer: TableViewerBase):
    """Make a copy of the current table."""
    table = _utils.get_table(viewer)
    viewer.add_table(table.data, name=f"{table.name}-copy")


def copy_as_spreadsheet(viewer: TableViewerBase):
    """Make a copy of the current table."""
    table = _utils.get_table(viewer)
    viewer.add_spreadsheet(table.data, name=f"{table.name}-copy")


def groupby(viewer: TableViewerBase):
    """Group table data by its column value."""
    table = _utils.get_table(viewer)
    out = _dialogs.groupby(
        df={"bind": table.data},
        by={"choices": list(table.data.columns), "widget_type": "Select"},
        parent=viewer._qwidget,
    )
    if out is not None:
        viewer.add_groupby(out, name=f"{table.name}-groupby")


def switch_header(viewer: TableViewerBase):
    """Switch header and the first row."""
    table = _utils.get_mutable_table(viewer)
    table._qwidget._switch_head_and_index(axis=1)


def concat(viewer: TableViewerBase):
    """Concatenate tables."""
    out = _dialogs.concat(
        viewer={"bind": viewer},
        names={
            "value": [viewer.current_table.name],
            "widget_type": "Select",
            "choices": [t.name for t in viewer.tables],
        },
        axis={"choices": [("vertical", 0), ("horizontal", 1)]},
        parent=viewer._qwidget,
    )
    if out is not None:
        viewer.add_table(out, name=f"concat")


def pivot(viewer: TableViewerBase):
    """Pivot a table."""
    table = _utils.get_table(viewer)
    col = list(table.data.columns)
    if len(col) < 3:
        raise ValueError("Table must have at least three columns.")
    out = _dialogs.pivot(
        df={"bind": table.data},
        index={"choices": col, "value": col[0]},
        columns={"choices": col, "value": col[1]},
        values={"choices": col, "value": col[2]},
        parent=viewer._qwidget,
    )
    if out is not None:
        viewer.add_table(out, name=f"{table.name}-pivot")


def melt(viewer: TableViewerBase):
    """Unpivot a table."""
    table = _utils.get_table(viewer)
    out = _dialogs.melt(
        df={"bind": table.data},
        id_vars={"choices": list(table.data.columns), "widget_type": "Select"},
        parent=viewer._qwidget,
    )
    if out is not None:
        viewer.add_table(out, name=f"{table.name}-melt")


def show_finder_widget(viewer: TableViewerBase):
    """Toggle finder"""
    return viewer._qwidget._tablestack.openFinderDialog()


def sort_table(viewer: TableViewerBase):
    """Add sorted table."""
    table = _utils.get_table(viewer)
    out = _dialogs.sort(
        df={"bind": table.data},
        by={"choices": list(table.data.columns), "widget_type": "Select"},
        ascending={"text": "Sort in ascending order."},
        parent=viewer._qwidget,
    )
    if out is not None:
        viewer.add_table(out, name=f"{table.name}-sorted")


def random(viewer: TableViewerBase):
    """Add random data to the specified data range."""
    table = viewer.current_table
    if table is None:
        return
    from ._random_data import RandomGeneratorDialog

    dlg = RandomGeneratorDialog()
    dlg.native.setParent(viewer._qwidget, dlg.native.windowFlags())
    dlg._selection_wdt._read_selection(table)
    dlg.show()

    @dlg.called.connect
    def _on_called():
        val = dlg.get_value(table._qwidget.model().df)
        rsl, csl, data = val
        table.cell[rsl, csl] = data


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


def show_undo_stack_view(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget.undoStackView()


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


def undo_table(viewer: TableViewerBase):
    _utils.get_mutable_table(viewer)._qwidget.undo()


def redo_table(viewer: TableViewerBase):
    _utils.get_mutable_table(viewer)._qwidget.redo()


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
