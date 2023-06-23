from __future__ import annotations
from typing import TYPE_CHECKING
from . import _dialogs, _utils
from tabulous._magicgui import ToggleSwitchSelect
from tabulous.widgets._source import Source

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase, TableBase, SpreadSheet
    from ._arange import _RangeDialog


def new_spreadsheet(viewer: TableViewerBase):
    """Add an empty spreadsheet."""
    viewer.add_spreadsheet()
    viewer.native.setCellFocus()


def copy_as_table(viewer: TableViewerBase):
    """Copy current table as a new table"""
    table = _utils.get_table(viewer)
    out = viewer.add_table(table.data, name=f"{table.name}-copy")
    out._source = Source.from_table(table)


def copy_as_spreadsheet(viewer: TableViewerBase):
    """Copy current table as a new spreadsheet"""
    table = _utils.get_table(viewer)
    out = viewer.add_spreadsheet(table.data, name=f"{table.name}-copy")
    out._source = Source.from_table(table)


def copy_to_clipboard(viewer: TableViewerBase):
    table = _utils.get_table(viewer)
    table._qwidget.dataShown().to_clipboard()
    return None


def switch_index(viewer: TableViewerBase):
    """Switch index header and the left column"""
    table = _utils.get_mutable_table(viewer)
    table._qwidget._switch_head_and_index(axis=0)


def switch_columns(viewer: TableViewerBase):
    """Switch column header and the top row"""
    table = _utils.get_mutable_table(viewer)
    table._qwidget._switch_head_and_index(axis=1)


def concat(viewer: TableViewerBase):
    """Concatenate table data (pd.concat)"""
    if len(viewer.tables) < 2:
        raise ValueError("At least two tables are required.")
    out = _dialogs.concat(
        viewer={"bind": viewer},
        names={
            "value": [viewer.current_table.name],
            "widget_type": ToggleSwitchSelect,
            "choices": [t.name for t in viewer.tables],
        },
        axis={"choices": [("vertical", 0), ("horizontal", 1)]},
        parent=viewer._qwidget,
    )
    if out is not None:
        table = viewer.add_table(out, name="concat")
        table._source = Source.from_table(viewer.current_table)


def merge(viewer: TableViewerBase):
    """Merge two tables (pd.merge)"""

    def _update_choices(wdt):
        table0: TableBase = wdt.merge.value
        table1: TableBase = wdt.with_.value
        if table0 is None or table1 is None:
            return
        col0 = table0.columns
        col1 = table1.columns
        choices = list(set(col0) & set(col1))
        wdt.on.choices = choices

    out = _dialogs.merge(
        merge={"changed": _update_choices},
        with_={"changed": _update_choices},
        how={"choices": ["left", "right", "outer", "inner"], "value": "inner"},
        on={"choices": [], "widget_type": ToggleSwitchSelect},
        parent=viewer._qwidget,
    )
    if out is not None:
        viewer.add_table(out, name="merged")


def pivot(viewer: TableViewerBase):
    """Pivot current table data (pd.pivot)"""
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
        table_out = viewer.add_table(out, name=f"{table.name}-pivot")
        table_out._source = Source.from_table(table)


def melt(viewer: TableViewerBase):
    """Melt (unpivot) current table data (pd.melt)"""
    table = _utils.get_table(viewer)
    cols = _utils.get_selected_columns(viewer)
    df = table.data
    out = df.melt(id_vars=[df.columns[i] for i in cols])
    if out is not None:
        table_out = viewer.add_table(out, name=f"{table.name}-melt")
        table_out._source = Source.from_table(table)


def transpose(viewer: TableViewerBase):
    """Transpose current table data"""
    table = _utils.get_table(viewer)
    out = table.data.T
    table_out = viewer.add_table(out, name=f"{table.name}-transposed")
    table_out._source = Source.from_table(table)


def fillna(viewer: TableViewerBase):
    """Fill nan values (pd.fillna)"""
    table = _utils.get_table(viewer)

    def _cb(mgui):
        mgui.value.visible = mgui.method.value == "value"

    _choices = [
        ("fill by value", "value"),
        ("forward fill", "ffill"),
        ("backward fill", "bfill"),
    ]
    out = _dialogs.fillna(
        df={"bind": table.data},
        method={
            "choices": _choices,
            "value": "value",
            "nullable": False,
            "changed": _cb,
        },
        value={"widget_type": "LiteralEvalLineEdit", "value": "0.0"},
        parent=viewer._qwidget,
    )
    if out is not None:
        table_out = viewer.add_table(out, name=f"{table.name}-fillna")
        table_out._source = Source.from_table(table)


def dropna(viewer: TableViewerBase):
    """Drop nan values (pd.dropna)"""
    table = _utils.get_table(viewer)
    out = _dialogs.dropna(
        df={"bind": table.data},
        axis={"choices": [("drop rows", 0), ("drop columns", 1)]},
        how={"choices": [("if any nan", "any"), ("if all nan", "all")]},
        parent=viewer._qwidget,
    )
    if out is not None:
        table_out = viewer.add_table(out, name=f"{table.name}-dropna")
        table_out._source = Source.from_table(table)


def show_finder_widget(viewer: TableViewerBase):
    """Toggle finder widget"""
    return viewer._qwidget._tablestack.openFinderDialog()


def reset_proxy(viewer: TableViewerBase) -> None:
    """Reset proxy (sort/filter)"""
    table = _utils.get_table(viewer)
    table.proxy.reset()
    return None


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


def round(viewer: TableViewerBase):
    """Round table data"""
    table = _utils.get_mutable_table(viewer)
    from magicgui.widgets import request_values

    out = request_values({"decimals": int}, parent=viewer._qwidget)
    if out is None:
        return
    decimals: int = out["decimals"]
    for sel in table.selections:
        selected_data = table.data_shown.iloc[sel]
        table.cell[sel] = selected_data.round(decimals)
    return None


def _run_range_dialog(dlg: _RangeDialog, viewer: TableViewerBase, table: TableBase):
    dlg.native.setParent(viewer._qwidget, dlg.native.windowFlags())
    dlg._selection._read_selection(table)
    dlg.show()

    @dlg.called.connect
    def _on_called():
        val = dlg.get_value(table._qwidget.model().df)
        rsl, csl, data = val
        c0 = csl.start
        was_empty = table.columns.size <= c0
        table.cell[rsl, c0] = data
        if was_empty and table.table_type == "SpreadSheet":
            _table: SpreadSheet = table
            _table.dtypes[_table.columns[c0]] = data.dtype


def date_range(viewer: TableViewerBase):
    """Generate a range of date values (pd.date_range)"""
    from ._arange import DateRangeDialog

    table = _utils.get_mutable_table(viewer)
    _run_range_dialog(DateRangeDialog(), viewer, table)


def timedelta_range(viewer: TableViewerBase):
    """Generate a range of timedelta values (pd.timedelta_range)"""
    from ._arange import TimeDeltaRangeDialog

    table = _utils.get_mutable_table(viewer)
    _run_range_dialog(TimeDeltaRangeDialog(), viewer, table)


def interval_range(viewer: TableViewerBase):
    """Generate a range of interval values (pd.interval_range)"""
    from ._arange import IntervalRangeDialog

    table = _utils.get_mutable_table(viewer)
    _run_range_dialog(IntervalRangeDialog(), viewer, table)


def period_range(viewer: TableViewerBase):
    """Generate a range of period values (pd.period_range)"""
    from ._arange import PeriodRangeDialog

    table = _utils.get_mutable_table(viewer)
    _run_range_dialog(PeriodRangeDialog(), viewer, table)


def toggle_editability(viewer: TableViewerBase):
    """Toggle table editability"""
    table = viewer.current_table
    try:
        table.editable = not table.editable
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


def zoom_in(viewer: TableViewerBase):
    """Zoom in"""
    table = _utils.get_table(viewer)
    table.native._qtable_view.zoomIn(1)


def zoom_out(viewer: TableViewerBase):
    """Zoom in"""
    table = _utils.get_table(viewer)
    table.native._qtable_view.zoomIn(-1)


def jump_to_cell(viewer: TableViewerBase):
    """Jump to a cell."""
    from tabulous._qt._jump import QJumpWidget

    if viewer.current_table is None:
        return
    jw = QJumpWidget(viewer.native)
    jw.show()
