from __future__ import annotations
from typing import Any
import pandas as pd

from ._base import AbstractDataFrameModel, QTableLayerBase

class DataFrameModel(AbstractDataFrameModel):
    
    @property
    def df(self) -> pd.DataFrame:
        return self._df
    
    @df.setter
    def df(self, data: pd.DataFrame):
        if data is self._df:
            return
        self.setShape(*data.shape)
        self._df = data
    
    def rowCount(self, parent=None):
        return self.df.shape[0]

    def columnCount(self, parent=None):
        return self.df.shape[1]


class QTableLayer(QTableLayerBase):

    def getDataFrame(self) -> pd.DataFrame:
        return self._data_raw

    def setDataFrame(self, data: pd.DataFrame) -> None:
        self._data_raw = data
        self.model().df = data
        self._filter_slice = None  # filter should be reset
        self.viewport().update()
        return

    def createModel(self) -> DataFrameModel:
        return DataFrameModel(self)
    
    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value to the type of the table."""
        kind = self._data_raw.dtypes[c].kind
        return _DTYPE_CONVERTER[kind](value)

def _bool_converter(val: Any):
    if isinstance(val, str):
        if val in ("True", "1", "true"):
            return True
        elif val in ("False", "0", "false"):
            return False
        else:
            raise ValueError(f"Cannot convert {val} to bool.")
    else:
        return bool(val)
    
_DTYPE_CONVERTER = {
    "i": int,
    "f": float,
    "u": int,
    "b": _bool_converter,
    "U": str,
    "O": lambda e: e,
    "c": complex,
    "M": pd.to_datetime,
    "m": pd.to_timedelta,
}
