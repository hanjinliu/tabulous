from tabulous import TableViewer
from tabulous._qt._table_stack._listwidget import QListTableStack
from tabulous._qt._table_stack._tabbar import QTabbedTableStack

def get_listwidget_tab_name(viewer: TableViewer, i: int) -> str:
    qtablist: QListTableStack = viewer._qwidget._tablist
    item = qtablist._tabs.item(i)
    qtab = qtablist._tabs.itemWidget(item)
    return qtab.text()

def get_tabwidget_tab_name(viewer: TableViewer, i: int) -> str:
    qtablist: QTabbedTableStack = viewer._qwidget._tablist
    return qtablist.tabText(i)
