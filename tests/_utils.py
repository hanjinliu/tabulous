from tabulous import TableViewer
from tabulous.widgets import TableBase
from tabulous._qt._table import QBaseTable
from tabulous._qt._table_stack._tabwidget import QTabbedTableStack

def get_tabwidget_tab_name(viewer: TableViewer, i: int) -> str:
    qtablist: QTabbedTableStack = viewer._qwidget._tablestack
    return qtablist.tabText(i)

def get_cell_value(table: QBaseTable, row, col):
    index = table.model().index(row, col)
    return table.model().data(index)

def edit_cell(table: QBaseTable, row, col, value):
    table.model().dataEdited.emit(row, col, value)

def slice_equal(s1: "tuple[slice, slice]", s2: "tuple[slice, slice]"):
    return (
        s1[0].start == s2[0].start and
        s1[1].start == s2[1].start and
        s1[0].stop == s2[0].stop and
        s1[1].stop == s2[1].stop
    )

def selection_equal(sel1: "list[tuple[slice, slice]]", sel2: "list[tuple[slice, slice]]"):
    if len(sel1) != len(sel2):
        return False
    for s1, s2 in zip(sel1, sel2):
        if not slice_equal(s1, s2):
            return False
    return True
