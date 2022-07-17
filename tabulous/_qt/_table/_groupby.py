from __future__ import annotations
from typing import Any, Hashable, Iterable, Sequence
import pandas as pd
from pandas.core.groupby.generic import DataFrameGroupBy
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Signal, Qt

from ._base import QBaseTable, _QTableViewEnhanced
from ._table import DataFrameModel

class _LabeledComboBox(QtW.QWidget):
    currentIndexChanged = Signal(int)
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._values = list[Any]
        _layout = QtW.QHBoxLayout()
        _layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        _layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(_layout)
        self._cbox = QtW.QComboBox()
        self._label = QtW.QLabel()
        _layout.addWidget(self._label)
        _layout.addWidget(self._cbox)
        
        self._cbox.currentIndexChanged.connect(self.currentIndexChanged.emit)
    
    def setLabel(self, text: str) -> None:
        """Set the text of label."""
        return self._label.setText(text)
    
    def setChoices(self, items: Iterable[Any]):
        """Set choices of combo box."""
        self._values = list(items)
        self._cbox.clear()
        return self._cbox.addItems(map(str, self._values))
    
    def currentIndex(self) -> int:
        """Get the current index of the choice."""
        return self._cbox.currentIndex()
    
    def setCurrentIndex(self, index: int) -> None:
        """Set current index."""
        return self._cbox.setCurrentIndex(index)
    
    def CurrentValue(self) -> Any:
        """Current value."""
        return self._values[self.currentIndex()]
    
    def setCurrentValue(self, value: Any) -> None:
        try:
            index = self._values.index(value)
        except ValueError:
            raise ValueError(f"{value} is not a valid choice.")
        return self.setCurrentIndex(index)


class QTableGroupBy(QBaseTable):
    _data_raw: DataFrameGroupBy

    @property
    def _qtable_view(self) -> _QTableViewEnhanced:
        return self._qtable_view_
    
    def createQTableView(self):
        self._qtable_view_ = _QTableViewEnhanced()
        self._group_key_cbox = _LabeledComboBox()
        self._group_map: dict[Hashable, Sequence[int]] = {}
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
        
        # set label
        keys = self._data_raw.keys
        if isinstance(keys, list):
            if len(keys) == 1:
                label = keys[0]
            else:
                label = tuple(keys)
        else:
            label = keys
        self._group_key_cbox.setLabel(f"{label} = ")
        
        self._group_map = self._data_raw.groups
        self._group_key_cbox.setChoices(self._group_map.keys())
        self.setFilter(None)
        self._qtable_view.viewport().update()
        return

    def createModel(self):
        model = DataFrameModel(self)
        self._qtable_view.setModel(model)
        return None

    def tableSlice(self) -> pd.DataFrame:
        df: pd.DataFrame = self._data_raw.obj
        sl = self._group_map[self._group_key_cbox.CurrentValue()]
        return df.iloc[sl, :]

    def currentGroup(self) -> Hashable:
        index = self._group_key_cbox.currentIndex()
        return self._group_key_cbox._values[index]
    
    def setCurrentGroup(self, group: Hashable) -> None:
        return self._group_key_cbox.setCurrentValue(group)