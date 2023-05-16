from tabulous import TableViewer, commands as cmds
import numpy as np

def test_groupby(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    sheet = viewer.add_spreadsheet({"a": np.arange(20), "b": np.arange(20) // 5})
    sheet.columns.selected = 1
    cmds.column.run_groupby(viewer)
    assert len(viewer.tables) == 2
