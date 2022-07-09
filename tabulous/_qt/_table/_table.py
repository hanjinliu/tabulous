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
            raise ValueError("DataFrame is deleted.")
        
        if self._filter_slice is None:
            return data
        elif callable(self._filter_slice):
            sl = self._filter_slice(data)
        else:
            sl = self._filter_slice
        return data[sl]    
    
    def refreshTable(self, data: pd.DataFrame | None = None):
        if data is not None:
            self._data_ref: weakref.ReferenceType[pd.DataFrame] = weakref.ref(data)
        data = self.getDataFrame()
        
        r0, c0, r1, c1 = self.getCurrentSquare()
        
        nr = self.rowCount()
        nc = self.columnCount()
        
        nr_data, nc_data = data.shape
        
        # check shape mismatch between DataFrame and table widget.
        if nr > nr_data:
            [self.removeRow(nr_data) for _ in range(nr - nr_data)]
        elif nr < nr_data:
            [self.insertRow(i) for i in range(nr_data - nr)]
        
        if nc > nc_data:
            [self.removeColumn(nc_data) for _ in range(nc - nc_data)]
        elif nc < nc_data:
            [self.insertColumn(i) for i in range(nc_data - nc)]
            
        r1 = min(r1, nr_data)
        c1 = min(c1, nc_data)
            
        vindex = data.index
        hindex = data.columns
        for r in range(r0, r1):
            vitem = self.verticalHeaderItem(r)
            text = str(vindex[r])
            if vitem is not None:
                vitem.setText(text)
            else:
                self.setVerticalHeaderItem(r, QtW.QTableWidgetItem(text))
            for c in range(c0, c1):
                item = self.item(r, c)
                text = str(data.iloc[r, c])
                if item is not None:
                    self.item(r, c).setText(text)
                else:
                    item = QtW.QTableWidgetItem(text)
                    self.setItem(r, c, item)
                # item.setBackground()
        
        for c in range(c0, c1):
            hitem = self.horizontalHeaderItem(c)
            text = str(hindex[c])
            if hitem is not None:
                hitem.setText(text)
            else:
                self.setHorizontalHeaderItem(c, QtW.QTableWidgetItem(text))
    
    def setDataFrameValue(self, r, c, value: Any) -> None:
        data = self._data_ref()
        if self._filter_slice is None:
            data.iloc[r, c] = value
            return
        elif callable(self._filter_slice):
            sl = self._filter_slice(data)
        else:
            sl = self._filter_slice
        
        cum = np.cumsum(sl)  # NOTE: this is not efficient if table is large
        if np.isscalar(r):
            r0 = np.where(cum == r + 1)[0]
            
        elif isinstance(r, slice):
            r_start, r_stop, r_step = r.indices(cum.shape[0])
            if r_step != 1:
                raise ValueError("step must not be >1.")
            start = np.where(cum == r_start + 1)[0][0]
            stop = np.where(cum == r_stop + 1)[0][0]
        
            r0 = np.array(sl, copy=True)
            r0[:start] = False
            r0[stop:] = False
            
        else:
            raise TypeError(type(r))
        
        data.iloc[r0, c] = value
        return None
        
    def normalizeData(self, row: int, col: int) -> ItemInfo:
        item = self.item(row, col)

        r = item.row()
        c = item.column()
        text = item.text()
        
        data = self._data_ref()
        dtype = data.dtypes[c]
        try:
            value = _DTYPE_KIND_TO_CONVERTER[dtype.kind](text)
        except Exception as e:
            self.refreshTable()
            updated = False
        else:
            self.setDataFrameValue(r, c, value)
            updated = True
        return ItemInfo(r, c, value, updated)


# TODO: datetime
_DTYPE_KIND_TO_CONVERTER = {
    "i": int,
    "f": float,
    "u": int,
    "U": str,
    "O": str,
    "c": complex,
}

