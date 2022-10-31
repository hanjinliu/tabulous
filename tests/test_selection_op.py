from tabulous._selection_op import ColumnSelOp, LocSelOp, ILocSelOp, SelectionOperator
import pandas as pd
from ._utils import slice_equal
import pytest

df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})

@pytest.mark.parametrize("cls", (ColumnSelOp, LocSelOp, ILocSelOp))
def test_well_defined(cls: "type[SelectionOperator]"):
    iloc_input = (slice(1, 3), slice(1, 2))
    op = cls.from_iloc(*iloc_input, df)
    iloc_output = op.as_iloc(df)
    assert slice_equal(iloc_input, iloc_output)

@pytest.mark.parametrize(
    ["cls", "expected"],
    [
        (ColumnSelOp, "df['b'][1:3]"),
        (LocSelOp, "df.loc[1:2, 'b':'b']"),
        (ILocSelOp, "df.iloc[1:3, 1:2]"),
    ]
)
def test_format(cls: "type[SelectionOperator]", expected: str):
    selop = cls.from_iloc(slice(1, 3), slice(1, 2), df)
    assert selop.fmt("df") == expected
