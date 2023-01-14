from tabulous import TableViewer
import numpy as np
import pandas as pd
import pytest
from typing import Callable

def test_setting_column_dtype():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"number": [1, 2, 3], "char": ["a", "b", "a"]})
    assert sheet.dtypes == {}

    sheet.dtypes["number"] = "float32"
    sheet.dtypes["char"] = "category"
    assert sheet.dtypes == {"number": "float32", "char": "category"}

    df = sheet.data
    assert df.dtypes[0] == "float32"
    assert df.dtypes[1] == "category"

    sheet.undo_manager.undo()
    assert sheet.dtypes == {"number": "float32"}

    sheet.undo_manager.undo()
    assert sheet.dtypes == {}

def test_datetime():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"datetime": ["2020-01-01", "2020-01-02", "2020-01-03"]})
    assert sheet.data.dtypes[0] == "object"

    sheet.dtypes["datetime"] = "datetime64[ns]"
    assert sheet.data.dtypes[0] == "datetime64[ns]"

def test_timedelta():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"timedelta": ["1d", "2d", "3d"]})
    assert sheet.data.dtypes[0] == "object"

    sheet.dtypes["timedelta"] = "timedelta64[ns]"
    assert sheet.data.dtypes[0] == "timedelta64[ns]"

def test_updating_column_name():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"number": [1, 2, 3], "char": ["a", "b", "a"]})

    sheet.dtypes["number"] = "float32"
    sheet.dtypes["char"] = "category"

    assert sheet.dtypes == {"number": "float32", "char": "category"}

    sheet.columns[0] = "new_name"

    assert sheet.dtypes == {"new_name": "float32", "char": "category"}

def test_deleting_column_name():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"number": [1, 2, 3], "char": ["a", "b", "a"]})

    sheet.dtypes["number"] = "float32"
    sheet.dtypes["char"] = "category"

    assert sheet.dtypes == {"number": "float32", "char": "category"}

    sheet.native.removeColumns(0, 1)

    assert sheet.dtypes == {"char": "category"}

@pytest.mark.parametrize(
    "dtype, fn",
    [("int", lambda n: pd.Series(np.arange(n), dtype=np.int32)),
     ("float", lambda n: pd.Series(np.arange(n), dtype=np.float64)),
     ("datetime64[ns]", lambda n: pd.date_range("2020/01/01", periods=n, freq="2D")),
     ("timedelta64[ns]", lambda n: pd.timedelta_range("00:00:00", periods=n, freq="60s")),
     ("interval", lambda n: pd.interval_range(0, periods=n, freq=1)),
     ],
)
def test_can_parse(dtype, fn: Callable[[int], pd.Series]):
    viewer = TableViewer(show=False)
    data = fn(5)
    sheet = viewer.add_spreadsheet({"c": data})
    sheet.dtypes["c"] = dtype
    assert sheet.dtypes["c"] == dtype
    assert sheet.data["c"].dtype == dtype
