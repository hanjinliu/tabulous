from tabulous import TableViewer
from tabulous._qt._table_stack._tabwidget import QTabbedTableStack

def get_tabwidget_tab_name(viewer: TableViewer, i: int) -> str:
    qtablist: QTabbedTableStack = viewer._qwidget._tablestack
    return qtablist.tabText(i)
