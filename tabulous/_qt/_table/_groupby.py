from __future__ import annotations
from typing import Any, Iterable
import pandas as pd
from pandas.core.groupby.generic import DataFrameGroupBy
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Signal, Qt

from ._base import QBaseTable
from ._table import DataFrameModel

class _LabeledComboBox(QtW.QWidget):
    currentIndexChanged = Signal(int)
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        _layout = QtW.QHBoxLayout()
        _layout.setAlignment(Qt.AlignLeft)
        _layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(_layout)
        self._cbox = QtW.QComboBox()
        self._label = QtW.QLabel()
        _layout.addWidget(self._label)
        _layout.addWidget(self._cbox)
        
        self._cbox.currentIndexChanged.connect(self.currentIndexChanged.emit)
    
    def setLabel(self, text: str) -> None:
        return self._label.setText(text)
    
    def clear(self):
        return self._cbox.clear()
    
    def addItems(self, items: Iterable[str]):
        return self._cbox.addItems(items)
    
    def currentIndex(self) -> int:
        return self._cbox.currentIndex()
    
    def setCurrentInex(self, index: int) -> None:
        return self._cbox.setCurrentIndex(index)

class QTableGroupBy(QBaseTable):
    _data_raw: DataFrameGroupBy

    @property
    def _qtable_view(self) -> QtW.QTableView:
        return self._qtable_view_
    
    def createQTableView(self):
        self._qtable_view_ = QtW.QTableView()
        self._group_key_cbox = _LabeledComboBox()
        self._group_map: list[Any] = []
        self._group_key_cbox.currentIndexChanged.connect(lambda e: self.setFilter(self._filter_slice))
                
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(_layout)
        self.layout().addWidget(self._group_key_cbox)
        self.layout().addWidget(self._qtable_view_)

    def getDataFrame(self) -> DataFrameGroupBy:
        return self._data_raw

    def setDataFrame(self, data: DataFrameGroupBy) -> None:
        if not isinstance(data, DataFrameGroupBy):
            raise TypeError(f"Data must be DataFrameGroupBy, not {type(data)}")
        self._data_raw = data
        self._group_key_cbox.setLabel(f"{self._data_raw.keys} = ")
        
        self._group_map = self._data_raw.groups
        self._group_map_keys = list(self._group_map.keys())
        self._group_key_cbox.clear()
        self._group_key_cbox.addItems(map(str, self._group_map_keys))
        self.setFilter(None)
        self._qtable_view.viewport().update()
        return

    def createModel(self):
        model = DataFrameModel(self)
        self._qtable_view.setModel(model)
        return None

    def tableSlice(self) -> pd.DataFrame:
        df: pd.DataFrame = self._data_raw.obj
        index = self._group_key_cbox.currentIndex()
        sl = self._group_map[self._group_map_keys[index]]
        return df.iloc[sl, :]
