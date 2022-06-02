from tabulous import TableViewer
import numpy as np


def test_add_layers():
    viewer = TableViewer(show=False)
    viewer.add_table({"a": [1, 2, 3], "b": [4, 5, 6]}, name="Data")
    df = viewer.tables[0].data
    assert viewer.current_index == 0
    agg = df.agg([np.mean, np.std])
    viewer.add_table(agg, name="Data")
    assert viewer.current_index == 1
    assert viewer.tables[0].name == "Data"
    assert viewer.tables[1].name == "Data-0"
    assert np.all(df == viewer.tables[0].data)
    assert np.all(agg == viewer.tables[1].data)
    