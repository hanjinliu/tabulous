from tabulous import TableViewer

def test_config_works(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    viewer.config
