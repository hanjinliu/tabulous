from __future__ import annotations
from typing import Any, TYPE_CHECKING
import numpy as np
from qtpy import QtCore
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
    """
    A table layer class that works similar to Excel sheet.
    
    Unlike ``QTableLayer``, this class does not have dtype. The dtype will be 
    determined every time table data is converted into DataFrame. Table data
    is (almost) unbounded.
    """
    
    def getDataFrame(self) -> pd.DataFrame:
        # TODO: dtype is not correctly inferred
        return self._data_raw.infer_objects()
    
    def setDataFrame(self, data: pd.DataFrame) -> None:
        self._data_raw = data.astype("string")
        self.model().df = data
        self._filter_slice = None  # filter should be reset
        self.update()
        return
    
    def createModel(self) -> SpreadSheetModel:
        return SpreadSheetModel(self)
    
    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value to the type of the table."""
        return value
    
    def readClipBoard(self):
        import pandas as pd
        return pd.read_clipboard(header=None).astype("string")
    
    def setDataFrameValue(self, r: int | slice, c: int | slice, value: Any) -> None:
        if isinstance(value, str) and value == "":
            return

        import pandas as pd
        nr, nc = self._data_raw.shape
        rmax = _get_limit(r)
        cmax = _get_limit(c)
        if nr <= rmax or nc <= cmax:
            if nr <= rmax:
                ext = pd.DataFrame(
                    np.full((rmax - nr + 1, nc), np.nan),
                    index=range(nr, rmax + 1),
                    dtype="string",
                )
                self._data_raw = pd.concat([self._data_raw, ext], axis=0)
            if nc <= cmax:
                ext = pd.DataFrame(
                    np.full((nr, cmax - nc + 1), np.nan),
                    columns=range(nc, cmax + 1),
                    dtype="string",
                )
                self._data_raw = pd.concat([self._data_raw, ext], axis=1, ignore_index=True)
            new_shape = self._data_raw.shape
            self.model().setShape(new_shape[0] + 10, new_shape[1] + 10)
            self.model().df = self._data_raw
        return super().setDataFrameValue(r, c, value)

def _get_limit(a):
    if isinstance(a, int):
        amax = a
    elif isinstance(a, slice):
        amax = a.stop
    else:
        raise TypeError(f"Cannot infer limit of type {type(a)}")
    return amax
