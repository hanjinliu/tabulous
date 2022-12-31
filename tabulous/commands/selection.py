from __future__ import annotations
from typing import TYPE_CHECKING
from magicgui import widgets as mwdg
from . import _utils, _dialogs

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase


def copy_data_tab_separated(viewer: TableViewerBase):
    """Copy cells (tab separated)"""
    viewer.copy_data(headers=False, sep="\t")


def copy_data_with_header_tab_separated(viewer: TableViewerBase):
    """Copy cells with headers (tab separated)"""
    viewer.copy_data(headers=True, sep="\t")


def copy_data_comma_separated(viewer: TableViewerBase):
    """Copy cells (comma separated)"""
    viewer.copy_data(headers=False, sep=",")


def copy_data_with_header_comma_separated(viewer: TableViewerBase):
    """Copy cells with headers (comma separated)"""
    viewer.copy_data(headers=True, sep=",")


def copy_as_literal(viewer: TableViewerBase):
    """Copy as literal"""
    _utils.get_table(viewer)._qwidget._copy_as_literal()


def copy_as_markdown(viewer: TableViewerBase):
    """Copy as markdown text"""
    _utils.get_table(viewer)._qwidget._copy_as_formated("markdown")


def copy_as_latex(viewer: TableViewerBase):
    """Copy as LaTeX text"""
    _utils.get_table(viewer)._qwidget._copy_as_formated("latex")


def copy_as_html(viewer: TableViewerBase):
    """Copy as HTML text"""
    _utils.get_table(viewer)._qwidget._copy_as_formated("html")


def copy_as_new_table(viewer: TableViewerBase):
    """Copy as new table"""
    _utils.get_table(viewer)._qwidget._copy_as_new_table(type_="table")


def copy_as_new_spreadsheet(viewer: TableViewerBase):
    """Copy as new spreadsheet"""
    _utils.get_table(viewer)._qwidget._copy_as_new_table(type_="spreadsheet")


def select_all(viewer: TableViewerBase):
    """Select all the cells"""
    _utils.get_table(viewer)._qwidget._qtable_view.selectAll()


def cut_data(viewer: TableViewerBase):
    """Cut selected cells"""
    qtable = _utils.get_mutable_table(viewer)._qwidget
    qtable.copyToClipboard(headers=False)
    qtable.deleteValues()


def paste_data_tab_separated(viewer: TableViewerBase):
    """Paste from tab separated text"""
    if table := _utils.get_mutable_table(viewer, None):
        table._qwidget.pasteFromClipBoard(sep="\t")
        return None

    import pandas as pd

    viewer.add_table(pd.read_clipboard(header=None, sep="\t"))
    return None


def paste_data_comma_separated(viewer: TableViewerBase):
    """Paste from comma separated text"""
    _utils.get_mutable_table(viewer)._qwidget.pasteFromClipBoard(sep=",")


def paste_data_from_numpy_string(viewer: TableViewerBase):
    """Paste from numpy-style text"""
    _utils.get_mutable_table(viewer)._qwidget._paste_numpy_str()


def delete_values(viewer: TableViewerBase):
    """Delete selected cells"""
    _utils.get_mutable_table(viewer)._qwidget.deleteValues()


def add_highlight(viewer: TableViewerBase):
    """Add highlight to cells"""
    qwidget = _utils.get_table(viewer)._qwidget
    qwidget.setHighlights(qwidget.highlights() + qwidget.selections())


def delete_selected_highlight(viewer: TableViewerBase):
    """Delete selected highlight"""
    table = _utils.get_table(viewer)._qwidget
    table._qtable_view._highlight_model.delete_selected()
    table._qtable_view._selection_model.set_ctrl(False)


def show_context_menu(viewer: TableViewerBase):
    """Execute context menu"""
    qtable = _utils.get_table(viewer)._qwidget
    qtable.showContextMenuAtIndex()


def raise_slot_error(viewer: TableViewerBase):
    """Show traceback at the cell"""
    qtable = _utils.get_table(viewer)._qwidget
    qtable.raiseSlotError()


def _notify_editability(viewer: TableViewerBase):
    """Notify that current table is not editable."""
    viewer._qwidget._tablestack.notifyEditability()


def set_column_dtype(viewer: TableViewerBase):
    """Set column specific dtype for data conversion and validation."""
    from tabulous._dtype import QDtypeWidget

    sheet = _utils.get_spreadsheet(viewer)._qwidget
    col = _utils.get_selected_column(viewer)
    if out := QDtypeWidget.requestValue(sheet):
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
    """Insert a row above"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return _notify_editability()
    row, _ = sheet._qtable_view._selection_model.current_index
    return sheet.insertRows(row, 1)


def insert_row_below(viewer: TableViewerBase):
    """Insert a row below"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return _notify_editability()
    row, _ = sheet._qtable_view._selection_model.current_index
    return sheet.insertRows(row + 1, 1)


def insert_column_left(viewer: TableViewerBase):
    """Insert a column left"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return _notify_editability()
    _, col = sheet._qtable_view._selection_model.current_index
    return sheet.insertColumns(col, 1)


def insert_column_right(viewer: TableViewerBase):
    """Insert a column right"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return _notify_editability()
    _, col = sheet._qtable_view._selection_model.current_index
    return sheet.insertColumns(col + 1, 1)


def remove_selected_rows(viewer: TableViewerBase):
    """Remove selected rows"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return _notify_editability()
    row, col = sheet._qtable_view._selection_model.current_index
    _, rng = sheet._qtable_view._selection_model.range_under_index(row, col)
    if rng is not None:
        row_range = rng[0]
        sheet.removeRows(row_range.start, row_range.stop - row_range.start)
        return None
    raise ValueError("No selection under cursor.")


def remove_selected_columns(viewer: TableViewerBase):
    """Remove selected columns"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    if not sheet.isEditable():
        return _notify_editability()
    row, col = sheet._qtable_view._selection_model.current_index
    _, rng = sheet._qtable_view._selection_model.range_under_index(row, col)
    if rng is not None:
        col_range = rng[1]
        sheet.removeColumns(col_range.start, col_range.stop - col_range.start)
        return None
    raise ValueError("No selection under cursor.")


def set_foreground_colormap(viewer: TableViewerBase) -> None:
    """Set foreground colormap to a column"""
    from ._colormap import exec_colormap_dialog

    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)

    column_name = sheet._filtered_columns[index]
    if cmap := exec_colormap_dialog(sheet._get_sub_frame(column_name), sheet):
        sheet.setForegroundColormap(column_name, cmap)
    return None


def reset_foreground_colormap(viewer: TableViewerBase) -> None:
    """Reset foreground colormap"""
    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)
    column_name = sheet._filtered_columns[index]
    return sheet.setForegroundColormap(column_name, None)


def set_background_colormap(viewer: TableViewerBase) -> None:
    """Set background colormap to a column"""
    from ._colormap import exec_colormap_dialog

    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)
    column_name = sheet._filtered_columns[index]
    if cmap := exec_colormap_dialog(sheet._get_sub_frame(column_name), sheet):
        sheet.setBackgroundColormap(column_name, cmap)
    return None


def reset_background_colormap(viewer: TableViewerBase) -> None:
    """Reset background colormap"""
    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)
    column_name = sheet._filtered_columns[index]
    return sheet.setBackgroundColormap(column_name, None)


def set_text_formatter(viewer: TableViewerBase) -> None:
    """Set text formatter"""
    from tabulous._text_formatter import exec_formatter_dialog

    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)
    column_name = sheet._filtered_columns[index]

    if fmt := exec_formatter_dialog(sheet.getDataFrame()[column_name], sheet):
        sheet.setTextFormatter(column_name, fmt)
    return None


def reset_text_formatter(viewer: TableViewerBase) -> None:
    """Reset text formatter"""
    sheet = _utils.get_table(viewer)._qwidget
    index = _utils.get_selected_column(viewer)
    column_name = sheet._filtered_columns[index]
    return sheet.setTextFormatter(column_name, None)


def write_data_signal_in_console(viewer: TableViewerBase):
    """Write data signal connection to console"""
    from qtpy import QtCore

    table = _utils.get_table(viewer)
    sels = table.selections
    if len(sels) != 1:
        return
    qviewer = viewer.native
    console = qviewer._console_widget
    if console is None or not console.isActive():
        delay = 500  # need delay to wait for the console to be activated
    else:
        delay = 0
    qviewer.setConsoleVisible(True)

    def _update_console():
        console = qviewer._console_widget
        rsl, csl = sels[0]
        if rsl == slice(None) and csl == slice(None):
            _getitem = ""
        else:
            r0 = str(rsl.start) if rsl.start is not None else ""
            r1 = str(rsl.stop) if rsl.stop is not None else ""
            c0 = str(csl.start) if csl.start is not None else ""
            c1 = str(csl.stop) if csl.stop is not None else ""
            _getitem = f"[{r0}:{r1}, {c0}:{c1}]"
        text = (
            f"@viewer.current_table.events.data{_getitem}.connect\n"
            "def _on_data_changed(info: 'ItemInfo'):\n"
            "    "
        )
        if buf := console.buffer():
            if not buf.endswith("\n"):
                buf += "\n"
            text = buf + text
        console.setBuffer(text)
        console.setFocus()
        console.setTempText("...")

    QtCore.QTimer.singleShot(delay, _update_console)
    return None


def write_slice_in_console(viewer: TableViewerBase) -> None:
    """Write data slice to console"""
    from qtpy import QtCore

    table = _utils.get_table(viewer)
    sels = table.selections
    if len(sels) != 1:
        return
    qviewer = viewer.native
    console = qviewer._console_widget
    if console is None or not console.isActive():
        delay = 500  # need delay to wait for the console to be activated
    else:
        delay = 0
    qviewer.setConsoleVisible(True)

    def _update_console():
        console = qviewer._console_widget
        rsl, csl = sels[0]
        if rsl.start is None:
            rsl_str = f"slice({rsl.stop})"
        elif rsl.stop is None:
            rsl_str = f"slice({rsl.start}, None)"
        else:
            rsl_str = f"slice({rsl.start}, {rsl.stop})"
        if csl.start is None:
            csl_str = f"slice({csl.stop})"
        elif csl.stop is None:
            csl_str = f"slice({csl.start}, None)"
        else:
            csl_str = f"slice({csl.start}, {csl.stop})"

        text = f"sl = ({rsl_str}, {csl_str})\n"
        if buf := console.buffer():
            if not buf.endswith("\n"):
                buf += "\n"
            text = buf + text
        console.setBuffer(text)
        console.setFocus()

    QtCore.QTimer.singleShot(delay, _update_console)
    return None


def write_data_reference_in_console(viewer: TableViewerBase) -> None:
    """Write data reference to console"""
    from qtpy import QtCore

    table = _utils.get_table(viewer)
    sels = table.selections
    if len(sels) != 1:
        return
    qviewer = viewer.native
    console = qviewer._console_widget
    if console is None or not console.isActive():
        delay = 500  # need delay to wait for the console to be activated
    else:
        delay = 0
    qviewer.setConsoleVisible(True)

    def _update_console():
        console = qviewer._console_widget
        rsl, csl = sels[0]
        r0 = rsl.start if rsl.start is not None else ""
        r1 = rsl.stop if rsl.stop is not None else ""
        c0 = csl.start if csl.start is not None else ""
        c1 = csl.stop if csl.stop is not None else ""

        text = f"viewer.data.iloc[{r0}:{r1}, {c0}:{c1}]"
        console.insertText(text)
        console.setFocus()

    QtCore.QTimer.singleShot(delay, _update_console)
    return None


def add_spinbox(viewer: TableViewerBase) -> None:
    """Add Spinbox"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    kwargs = _dialogs.spinbox(parent=viewer.native)
    with sheet._mgr.merging():
        for r, c in sheet._qtable_view._selection_model.iter_all_indices():
            sheet._set_widget_at_index(r, c, mwdg.SpinBox(**kwargs))
    return None


def add_float_spinbox(viewer: TableViewerBase) -> None:
    """Add FloatSpinBox"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    kwargs = _dialogs.float_spinbox(parent=viewer.native)
    with sheet._mgr.merging():
        for r, c in sheet._qtable_view._selection_model.iter_all_indices():
            sheet._set_widget_at_index(r, c, mwdg.FloatSpinBox(**kwargs))
    return None


def add_slider(viewer: TableViewerBase) -> None:
    """Add Slider"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    kwargs = _dialogs.slider(parent=viewer.native)
    with sheet._mgr.merging():
        for r, c in sheet._qtable_view._selection_model.iter_all_indices():
            sheet._set_widget_at_index(r, c, mwdg.Slider(**kwargs))
    return None


def add_float_slider(viewer: TableViewerBase) -> None:
    """Add FloatSlider"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    kwargs = _dialogs.float_slider(parent=viewer.native)
    with sheet._mgr.merging():
        for r, c in sheet._qtable_view._selection_model.iter_all_indices():
            sheet._set_widget_at_index(r, c, mwdg.FloatSlider(**kwargs))
    return None


def add_checkbox(viewer: TableViewerBase) -> None:
    """Add CheckBox"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    kwargs = _dialogs.checkbox(parent=viewer.native)
    with sheet._mgr.merging():
        for r, c in sheet._qtable_view._selection_model.iter_all_indices():
            sheet._set_widget_at_index(r, c, mwdg.CheckBox(**kwargs))
    return None


def add_radio_button(viewer: TableViewerBase) -> None:
    """Add RadioButton"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    kwargs = _dialogs.radio_button(parent=viewer.native)
    with sheet._mgr.merging():
        for r, c in sheet._qtable_view._selection_model.iter_all_indices():
            sheet._set_widget_at_index(r, c, mwdg.RadioButton(**kwargs))
    return None


def add_line_edit(viewer: TableViewerBase) -> None:
    """Add LineEdit"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    with sheet._mgr.merging():
        for r, c in sheet._qtable_view._selection_model.iter_all_indices():
            sheet._set_widget_at_index(r, c, mwdg.LineEdit())
    return None


def remove_cell_widgets(viewer: TableViewerBase) -> None:
    """Remove cell widgets"""
    sheet = _utils.get_spreadsheet(viewer)._qwidget
    with sheet._mgr.merging():
        for r, c in sheet._qtable_view._selection_model.iter_all_indices():
            sheet._set_widget_at_index(r, c, None)
    return None


def edit_current(viewer: TableViewerBase) -> None:
    """Edit current cell"""
    table = _utils.get_table(viewer)._qwidget
    table._qtable_view._edit_current()
    return None


def sort_by_columns(viewer: TableViewerBase) -> None:
    """Sort by column(s)"""
    table = _utils.get_table(viewer)
    indices = _utils.get_selected_columns(viewer)
    by = [table.columns[index] for index in indices]
    return table.proxy.sort(by=by)


def filter_by_columns(viewer: TableViewerBase) -> None:
    """Filter by a column"""
    from tabulous._qt._proxy_button import QHeaderFilterButton

    table = _utils.get_table(viewer)
    indices = _utils.get_selected_columns(viewer)
    by = [table.columns[index] for index in indices]
    QHeaderFilterButton.from_table(table, by)
    return None


def shuffle_data_column_wise(viewer: TableViewerBase) -> None:
    """Shuffle table data columnwise"""
    table = _utils.get_mutable_table(viewer)
    for sel in table.selections:
        selected_data = table._qwidget.dataShown(parse=False).iloc[sel]
        shuffled = selected_data.sample(frac=1)
        shuffled.reset_index()
        table.cell[sel] = shuffled
    return None
