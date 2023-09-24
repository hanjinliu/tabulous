from __future__ import annotations
from tabulous._selection_op import (
    ColumnSelOp, LocSelOp, ILocSelOp, ValueSelOp, SelectionOperator, iter_extract
)
import pandas as pd
from ._utils import slice_equal
import pytest

df_str = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})
df_int = pd.DataFrame({0: [1, 2, 3], 2: [4, 5, 6], 7: [7, 8, 9]})

@pytest.mark.parametrize("cls", (ColumnSelOp, LocSelOp, ILocSelOp, ValueSelOp))
def test_well_defined_str(cls: type[SelectionOperator]):
    iloc_input = (slice(1, 3), slice(1, 2))
    op = cls.from_iloc(*iloc_input, df_str)
    iloc_output = op.as_iloc(df_str)
    assert slice_equal(iloc_input, iloc_output)

@pytest.mark.parametrize(
    ["cls", "expected"],
    [
        (ColumnSelOp, "df['b'][1:3]"),
        (LocSelOp, "df.loc[1:2, 'b':'b']"),
        (ILocSelOp, "df.iloc[1:3, 1:2]"),
        (ValueSelOp, "df.values[1:3, 1:2]"),
    ]
)
def test_format_str(cls: type[SelectionOperator], expected: str):
    selop = cls.from_iloc(slice(1, 3), slice(1, 2), df_str)
    assert selop.fmt("df") == expected

@pytest.mark.parametrize("cls", (ColumnSelOp, LocSelOp, ILocSelOp, ValueSelOp))
def test_well_defined_int(cls: type[SelectionOperator]):
    iloc_input = (slice(1, 3), slice(1, 2))
    op = cls.from_iloc(*iloc_input, df_int)
    iloc_output = op.as_iloc(df_int)
    assert slice_equal(iloc_input, iloc_output)

@pytest.mark.parametrize(
    ["cls", "expected"],
    [
        (ColumnSelOp, "df[2][1:3]"),
        (LocSelOp, "df.loc[1:2, 2:2]"),
        (ILocSelOp, "df.iloc[1:3, 1:2]"),
        (ValueSelOp, "df.values[1:3, 1:2]"),
    ]
)
def test_format_int(cls: type[SelectionOperator], expected: str):
    selop = cls.from_iloc(slice(1, 3), slice(1, 2), df_int)
    assert selop.fmt("df") == expected


@pytest.mark.parametrize(
    ["expr", "expected"],
    [
        ("np.mean(df.iloc[1:3, 10:20]) + df.loc[1:2, 'a':'col']",
         [ILocSelOp(slice(1, 3), slice(10, 20)), LocSelOp(slice(1, 2), slice("a", "col"))]),
        ("np.mean(df.iloc[:, 10:20]) + df.loc[:, 'a']",
         [ILocSelOp(slice(None), slice(10, 20)), LocSelOp(slice(None), "a")]),
        ("df[0][3:6].mean()",
         [ColumnSelOp(0, slice(3, 6))]),
        ("df[0][:].mean()",
         [ColumnSelOp(0, slice(None))]),
        ("df['0'][:].mean()",
         [ColumnSelOp('0', slice(None))]),
        ("df.values[3:6, 10:20] + df.iloc[1:2, 1:2]",
         [ValueSelOp(slice(3, 6), slice(10, 20)), ILocSelOp(slice(1, 2), slice(1, 2))]
         ),
    ]
)
def test_extract(expr: str, expected: list[SelectionOperator]):
    result = list(iter_extract(expr))
    assert result == expected
