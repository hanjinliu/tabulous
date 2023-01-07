from tabulous.widgets import Table
import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal, assert_series_equal

def assert_obj_equal(a, b):
    if isinstance(a, pd.DataFrame):
        assert_frame_equal(a, b)
    else:
        assert_series_equal(a, b)

@pytest.mark.parametrize(
    "sl",
    [
        slice(None),
        slice(1, 4),
        (slice(None), slice(None)),
        (slice(None), "A"),
        (slice(None), slice("A", "C")),
        (slice(None), slice("B", "B")),
        (slice(None), slice("C", None)),
        (slice(None), slice(None, "B")),
        (slice(None), ["B", "D"]),
        ([1, 3, 6], "B"),
    ]
)
def test_loc_data_equal(sl):
    df = pd.DataFrame(np.arange(50).reshape(10, 5), columns=list("ABCDE"))
    table = Table(df)
    assert_obj_equal(table.loc[sl].data, table.data.loc[sl])

@pytest.mark.parametrize(
    "sl",
    [
        slice(None),
        slice(1, 4),
        (slice(None), slice(None)),
        (slice(None), 0),
        (slice(None), slice(0, 3)),
        (slice(None), slice(1, 2)),
        (slice(None), slice(3, None)),
        (slice(None), slice(None, 3)),
        (slice(None), [1, 3]),
        ([1, 3, 6], 1),
    ]
)
def test_iloc_data_equal(sl):
    df = pd.DataFrame(np.arange(50).reshape(10, 5), columns=list("ABCDE"))
    table = Table(df)
    assert_obj_equal(table.iloc[sl].data, table.data.iloc[sl])
