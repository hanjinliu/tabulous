from __future__ import annotations
from typing import TYPE_CHECKING
from . import _dialogs, _utils

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase


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


def copy_data(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget.copyToClipboard(header=False)


def copy_data_with_header(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget.copyToClipboard(header=True)


# TODO: other copy as


def show_undo_stack_view(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget.undoStackView()


def copy_as_new_table(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget.undoStackView()


def select_all(viewer: TableViewerBase):
    _utils.get_table(viewer)._qwidget._qtable_view.selectAll()


def cut_data(viewer: TableViewerBase):
    qtable = _utils.get_mutable_table(viewer)._qwidget
    qtable.copyToClipboard(headers=False)
    qtable.deleteValues()


def paste_data(viewer: TableViewerBase):
    _utils.get_mutable_table(viewer)._qwidget.pasteFromClipBoard()


def delete_values(viewer: TableViewerBase):
    _utils.get_mutable_table(viewer)._qwidget.deleteValues()


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
