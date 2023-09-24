from tabulous import TableViewer
from tabulous._qt._table import QTableGroup
import pandas as pd
import pytest

df0 = pd.DataFrame({"a": [10, 20, 30]})
df1 = pd.DataFrame({"b": ["one", "two", "one"]})
df2 = pd.DataFrame({"c": [True, False, True]})
df3 = pd.DataFrame({"d": [1.0, 1.0, 2.0]})

def _is_group(viewer: TableViewer, index: int) -> bool:
    return isinstance(viewer._qwidget._tablestack.widget(index), QTableGroup)

@pytest.mark.parametrize("indices", [[0, 1], [2, 0], [0, 1, 2], [0, 2, 3]])
def test_merge(indices, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    viewer.add_table(df0)
    viewer.add_table(df1)
    viewer.add_table(df2)
    viewer.add_table(df3)

    viewer.tables.tile(indices)

    for i in indices:
        assert _is_group(viewer, i)
        table = viewer.tables[i]
        qtable = viewer._qwidget._tablestack.tableAtIndex(i)
        assert table._qwidget is qtable

def test_merge_error(make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    viewer.add_table(df0)
    viewer.add_table(df1)
    viewer.add_table(df2)
    viewer.add_table(df3)

    with pytest.raises(Exception):
        viewer.tables.tile([0, 4])
    with pytest.raises(Exception):
        viewer.tables.tile([0, 0])
    with pytest.raises(Exception):
        viewer.tables.tile([0.0, 4])
    with pytest.raises(Exception):
        viewer.tables.tile([1])

@pytest.mark.parametrize("indices", [[0, 1], [2, 0]])
def test_unmerge_2(indices, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    viewer.add_table(df0)
    viewer.add_table(df1)
    viewer.add_table(df2)
    viewer.add_table(df3)

    viewer.tables.tile(indices)
    viewer.tables.untile(0)

    for i in [0, 1, 2, 3]:
        assert not _is_group(viewer, i)
        table = viewer.tables[i]
        qtable = viewer._qwidget._tablestack.tableAtIndex(i)
        assert table._qwidget is qtable

    viewer.tables.tile(indices)  # test merging again just works

@pytest.mark.parametrize("indices", [[0, 1, 2], [0, 1, 3], [2, 0, 3]])
def test_unmerge_3(indices, make_tabulous_viewer):
    viewer: TableViewer = make_tabulous_viewer()
    viewer.add_table(df0)
    viewer.add_table(df1)
    viewer.add_table(df2)
    viewer.add_table(df3)

    viewer.tables.tile(indices)
    viewer.tables.untile(indices)

    for i in [0, 1, 2, 3]:
        assert not _is_group(viewer, i)
        table = viewer.tables[i]
        qtable = viewer._qwidget._tablestack.tableAtIndex(i)
        assert table._qwidget is qtable

    viewer.tables.tile(indices)  # test merging again just works
