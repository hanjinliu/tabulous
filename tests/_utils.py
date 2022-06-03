from tabulous import TableViewer

def get_tab_name(viewer: TableViewer, i: int) -> str:
    qtablist = viewer._qwidget._tablist
    item = qtablist.item(i)
    qtab = qtablist.itemWidget(item)
    return qtab.text()
    