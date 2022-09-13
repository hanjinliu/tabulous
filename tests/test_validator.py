from tabulous import TableViewer
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

def test_validator():
    viewer = TableViewer(show=False)
    table = viewer.add_table(
        {"number": [1, 2, 3], "char": ["a", "b", "c"]},
        editable=True,
    )
    @table.validator("number")
    def _validator(x):
        if x < 0:
            raise ValueError("Negative numbers are not allowed")

    table.cell[0, 0] = 2  # no error
    assert table.cell[0, 0] == 2

    # validation error
    with pytest.raises(ValueError):
        table.cell[0, 0] = -1
    assert table.cell[0, 0] == 2

def test_validator_on_paste():
    viewer = TableViewer(show=False)
    table = viewer.add_table(
        {"a": [1, 2, 3], "b": [1, 2, 3]},
        editable=True,
    )

    @table.validator("a")
    @table.validator("b")
    def _validator(x):
        if x < 0:
            raise ValueError("Negative numbers are not allowed")

    df = pd.DataFrame({"a": [1, 3, 1], "b": [1, 3, 1]})
    df.to_clipboard(index=False, header=False)
    viewer.paste_data([(slice(None), slice(None))])
    assert_frame_equal(table.data, df)

    df_err = pd.DataFrame({"a": [1, 1, 1], "b": [1, -1, 1]})
    df_err.to_clipboard(index=False, header=False)
    with pytest.raises(ValueError):
        viewer.paste_data([(slice(None), slice(None))])
    assert_frame_equal(table.data, df)  # don't change data
