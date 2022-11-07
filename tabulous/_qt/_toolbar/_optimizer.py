from __future__ import annotations
from typing import TYPE_CHECKING
from scipy.optimize import minimize
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from .._table._base import QMutableSimpleTable


def minimize_in_table(
    table: QMutableSimpleTable,
    dst: tuple[int, int],
    params: tuple[slice, slice],
):
    # TODO: check params are included in ref
    def fun(*p):
        table.setDataFrameValue(*params, pd.DataFrame(p).transpose())
        val = table.dataShown().iat[dst]
        return float(val)

    data = table.dataShown().iloc[params]
    param0 = data.to_numpy(dtype=np.float64, copy=False)

    return minimize(fun, param0, callback=lambda x: table.refreshTable(True))
