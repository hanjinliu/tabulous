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
        # TODO: dtype is not correctly inferred
        return self._data_raw.infer_objects()

    def createModel(self) -> SpreadSheetModel:
        return SpreadSheetModel(self)
    
    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value to the type of the table."""
        return value
    
    def setDataFrameValue(self, r: int | slice, c: int | slice, value: Any) -> None:
        nr, nc = self._data_raw.shape
        rmax = _get_limit(r)
        cmax = _get_limit(c)
        if nr <= rmax or nc <= cmax:
            import pandas as pd
            if nr <= rmax:
                ext = pd.DataFrame(
                    np.full((rmax - nr + 1, nc), np.nan, dtype=object),
                    index=range(nr, rmax + 1),
                )
                self._data_raw = pd.concat([self._data_raw, ext], axis=0, ignore_index=True)
            if nc <= cmax:
                ext = pd.DataFrame(
                    np.full((nr, cmax - nc + 1), np.nan, dtype=object),
                    columns=range(nc, cmax + 1),
                )
                self._data_raw = pd.concat([self._data_raw, ext], axis=1, ignore_index=True)
            
            self.model().df = self._data_raw
        super().setDataFrameValue(r, c, value)

def _get_limit(a):
    if isinstance(a, int):
        amax = a
    elif isinstance(a, slice):
        amax = a.stop
    else:
        raise TypeError(f"Cannot infer limit of type {type(a)}")
    return amax
