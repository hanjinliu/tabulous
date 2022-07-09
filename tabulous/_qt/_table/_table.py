from __future__ import annotations
from typing import Any, TYPE_CHECKING
import weakref
import numpy as np
from qtpy import QtWidgets as QtW

from ._table_base import QTableLayerBase, ItemInfo

if TYPE_CHECKING:
    import pandas as pd


class QTableLayer(QTableLayerBase):

    def getDataFrame(self) -> pd.DataFrame:
        data = self._data_ref()
        if data is None:
            raise ValueError("DataFrame has been deleted.")
        return data

