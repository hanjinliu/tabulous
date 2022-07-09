from __future__ import annotations
from typing import Any, TYPE_CHECKING
from qtpy import QtWidgets as QtW
import numpy as np
from ._table_base import QTableLayerBase
from ._model import DataFrameModel, SpreadSheetModel

if TYPE_CHECKING:
    import pandas as pd


class QTableLayer(QTableLayerBase):

    def getDataFrame(self) -> pd.DataFrame:
        return self._data_raw

    def createModel(self) -> DataFrameModel:
        return DataFrameModel(self)
    
    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value to the type of the table."""
        kind = self._data_raw.dtypes[c].kind
        return _DTYPE_CONVERTER[kind](value)

# TODO: datetime
_DTYPE_CONVERTER = {
    "i": int,
    "f": float,
    "u": int,
    "b": bool,
    "U": str,
    "O": str,
    "c": complex,
}

class QSpreadSheet(QTableLayerBase):
    
    def getDataFrame(self) -> pd.DataFrame:
        return self._data_raw.infer_objects()

    def createModel(self) -> SpreadSheetModel:
        return SpreadSheetModel(self)
    
    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value to the type of the table."""
        return value
    
    def setDataFrameValue(self, r: int, c: int, value: Any) -> None:
        nr, nc = self._data_raw.shape
        if nr <= r or nc <= c:
            import pandas as pd
            if nr <= r:
                ext = pd.DataFrame(
                    np.full((r - nr + 1, nc), np.nan, dtype=object),
                    index=range(nr, r + 1),
                )
                self._data_raw = pd.concat([self._data_raw, ext], axis=0, ignore_index=True)
            if nc <= c:
                ext = pd.DataFrame(
                    np.full((nr, c - nc + 1), np.nan, dtype=object),
                    columns=range(nc, c + 1),
                )
                self._data_raw = pd.concat([self._data_raw, ext], axis=1, ignore_index=True)
            self.model().df = self._data_raw
        super().setDataFrameValue(r, c, value)
