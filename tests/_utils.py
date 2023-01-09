from __future__ import annotations
from tabulous import TableViewer
from tabulous.widgets import TableBase
from tabulous._qt._table import QBaseTable
from tabulous._qt._table_stack._tabwidget import QTabbedTableStack
from qtpy.QtCore import Qt

def get_tabwidget_tab_name(viewer: TableViewer, i: int) -> str:
    qtablist: QTabbedTableStack = viewer._qwidget._tablestack
    return qtablist.tabText(i)

def edit_cell(table: QBaseTable, row, col, value):
    table.model().dataEdited.emit(row, col, value)

def slice_equal(s1: tuple[int | slice, int | slice], s2: tuple[int | slice, int | slice]):
    s1 = slice(_normalize_val(s1[0]), _normalize_val(s1[1]))
    s2 = slice(_normalize_val(s2[0]), _normalize_val(s2[1]))
    return s1 == s2

def _normalize_val(s: int | slice) -> slice:
    if isinstance(s, int):
        return slice(s, s + 1)
    return s

def selection_equal(sel1: list[tuple[slice, slice]], sel2: list[tuple[slice, slice]]):
    if len(sel1) != len(sel2):
        return False
    for s1, s2 in zip(sel1, sel2):
        if not slice_equal(s1, s2):
            return False
    return True
