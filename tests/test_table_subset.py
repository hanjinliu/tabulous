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

DATA = pd.DataFrame(np.arange(50).reshape(10, 5), columns=list("ABCDE"))

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
    table = Table(DATA)
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
    table = Table(DATA)
    assert_obj_equal(table.iloc[sl].data, table.data.iloc[sl])

def test_partial_text_color():
    table = Table(DATA)

    assert table["B"].text_color.item() is None
    table["B"].text_color.set(interp_from=["red", "blue"])
    assert table["B"].text_color.item() is not None
    assert table["B"].text_color.item() is table.text_color["B"]
    assert table.cell.text_color[0, 1].equals("red")

    table["B"].text_color.reset()
    assert table["B"].text_color.item() is None

def test_partial_background_color():
    table = Table(DATA)

    assert table["B"].background_color.item() is None
    table["B"].background_color.set(interp_from=["red", "blue"])
    assert table["B"].background_color.item() is not None
    assert table["B"].background_color.item() is table.background_color["B"]
    assert table.cell.background_color[0, 1].equals("red")

    table["B"].background_color.reset()
    assert table["B"].background_color.item() is None

def test_partial_formatter():
    table = Table(DATA)

    assert table["B"].formatter.item() is None
    table["B"].formatter.set(lambda x: "test")
    assert table["B"].formatter.item() is not None
    assert table.cell.text[0, 1] == "test"

    table["B"].formatter.reset()
    assert table["B"].formatter.item() is None

def test_partial_validator():
    table = Table(DATA, editable=True)

    def _raise(x):
        raise ValueError

    table["B"].validator.set(_raise)
    with pytest.raises(ValueError):
        table.cell[0, 1] = "6"

    table["B"].validator.reset()
    table.cell[0, 1] = "6"
