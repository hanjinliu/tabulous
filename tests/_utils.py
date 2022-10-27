from tabulous import TableViewer
from tabulous.widgets import TableBase
from tabulous._qt._table import QBaseTable
from tabulous._qt._table_stack._tabwidget import QTabbedTableStack
from qtpy.QtCore import Qt

def get_tabwidget_tab_name(viewer: TableViewer, i: int) -> str:
    qtablist: QTabbedTableStack = viewer._qwidget._tablestack
    return qtablist.tabText(i)

def get_cell_value(table: QBaseTable, row, col) -> str:
    index = table.model().index(row, col)
    return table.model().data(index)

def get_cell_foreground_color(table: QBaseTable, row, col) -> str:
    index = table.model().index(row, col)
    return table.model().data(index, Qt.ItemDataRole.ForegroundRole)

def get_cell_background_color(table: QBaseTable, row, col) -> str:
    index = table.model().index(row, col)
    return table.model().data(index, Qt.ItemDataRole.BackgroundRole)

def edit_cell(table: QBaseTable, row, col, value):
    table.model().dataEdited.emit(row, col, value)

def slice_equal(s1: "tuple[slice, slice]", s2: "tuple[int | slice, int | slice]"):
    x0, x1 = s2
    if isinstance(x0, int):
        x0 = slice(x0, x0 + 1)
    if isinstance(x1, int):
        x1 = slice(x1, x1 + 1)
    return (
        s1[0].start == x0.start and
        s1[1].start == x1.start and
        s1[0].stop == x0.stop and
        s1[1].stop == x1.stop
    )

def selection_equal(sel1: "list[tuple[slice, slice]]", sel2: "list[tuple[slice, slice]]"):
    if len(sel1) != len(sel2):
        return False
    for s1, s2 in zip(sel1, sel2):
        if not slice_equal(s1, s2):
            return False
    return True
