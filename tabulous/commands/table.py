from __future__ import annotations
from typing import TYPE_CHECKING
from . import _dialogs, _utils

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase


def new_spreadsheet(viewer: TableViewerBase):
    """Add an empty spreadsheet."""
    viewer.add_spreadsheet()


def copy_as_table(viewer: TableViewerBase):
    """Copy current table as a new table"""
    table = _utils.get_table(viewer)
    viewer.add_table(table.data, name=f"{table.name}-copy")


def copy_as_spreadsheet(viewer: TableViewerBase):
    """Copy current table as a new spreadsheet"""
    table = _utils.get_table(viewer)
    viewer.add_spreadsheet(table.data, name=f"{table.name}-copy")


def copy_to_clipboard(viewer: TableViewerBase):
    table = _utils.get_table(viewer)
    table._qwidget.dataShown().to_clipboard()
    return None


def groupby(viewer: TableViewerBase):
    """Group table data by its column(s)"""
    table = _utils.get_table(viewer)
    out = _dialogs.groupby(
        df={"bind": table.data},
        by={"choices": list(table.data.columns), "widget_type": "Select"},
        parent=viewer._qwidget,
    )
    if out is not None:
        viewer.add_groupby(out, name=f"{table.name}-groupby")


def switch_header(viewer: TableViewerBase):
    """Switch header and the top row"""
    table = _utils.get_mutable_table(viewer)
    table._qwidget._switch_head_and_index(axis=1)


def concat(viewer: TableViewerBase):
    """Concatenate table data"""
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
    """Pivot current table data"""
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
    """Melt (unpivot) current table data"""
    table = _utils.get_table(viewer)
    out = _dialogs.melt(
        df={"bind": table.data},
        id_vars={"choices": list(table.data.columns), "widget_type": "Select"},
        parent=viewer._qwidget,
    )
    if out is not None:
        viewer.add_table(out, name=f"{table.name}-melt")


def show_finder_widget(viewer: TableViewerBase):
    """Toggle finder widget"""
    return viewer._qwidget._tablestack.openFinderDialog()


def sort_table(viewer: TableViewerBase):
    """Sort table data"""
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
    """Generate random values"""
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


def toggle_editability(viewer: TableViewerBase):
    """Toggle table editability."""
    table = viewer.current_table
    try:
        table.editable = not table.editable
        viewer.native._tablestack._notifier.setVisible(False)
    except Exception:
        pass
    viewer.native.setCellFocus()


def show_undo_stack_view(viewer: TableViewerBase):
    """Show undo stack view"""
    _utils.get_table(viewer)._qwidget.undoStackView()


def undo_table(viewer: TableViewerBase):
    """Undo table operation"""
    _utils.get_mutable_table(viewer)._qwidget.undo()


def redo_table(viewer: TableViewerBase):
    """Redo table operation"""
    _utils.get_mutable_table(viewer)._qwidget.redo()


def switch_layout(viewer: TableViewerBase):
    """Switch table layout"""
    table = _utils.get_table(viewer)
    if table.layout == "vertical":
        table.layout = "horizontal"
    else:
        table.layout = "vertical"
