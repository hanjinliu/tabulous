from __future__ import annotations
from typing import Any
import pandas as pd

from ._base import QMutableSimpleTable, DataFrameModel
from ._dtype import convert_value


class QTableLayer(QMutableSimpleTable):
    def getDataFrame(self) -> pd.DataFrame:
        return self._data_raw

    @QMutableSimpleTable._mgr.interface
    def setDataFrame(self, data: pd.DataFrame) -> None:
        self._data_raw = data
        self.model().df = data
        self.setFilter(None)
        self._qtable_view.viewport().update()
        return

    @setDataFrame.server
    def setDataFrame(self, data):
        try:
            return (self.getDataFrame(),), {}
        except Exception:
            return None

    @setDataFrame.set_formatter
    def _setDataFrame_fmt(self, data: pd.DataFrame):
        return f"set new data of shape {data.shape}"

    def createModel(self):
        model = DataFrameModel(self)
        self._qtable_view.setModel(model)
        return None

    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value to the type of the table."""
        kind = self._data_raw.dtypes[c].kind
        return convert_value(kind, value)
