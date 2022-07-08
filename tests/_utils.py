from tabulous import TableViewer
from tabulous._qt._table_stack._listwidget import QListTableStack

# Only works with QListTableStack
def get_tab_name(viewer: TableViewer, i: int) -> str:
    qtablist: QListTableStack = viewer._qwidget._tablist
    item = qtablist._tabs.item(i)
    qtab = qtablist._tabs.itemWidget(item)
    return qtab.text()
    