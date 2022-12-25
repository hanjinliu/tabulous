from __future__ import annotations
from typing import Any, Hashable, Iterable, Sequence, TYPE_CHECKING
from pandas.core.groupby.generic import DataFrameGroupBy
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Signal, Qt
from collections_undo import arguments

from ._base import QBaseTable, _QTableViewEnhanced, DataFrameModel

if TYPE_CHECKING:
    import pandas as pd


class _QLabeledComboBox(QtW.QWidget):
    currentIndexChanged = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._values: list[Any] = []
        _layout = QtW.QHBoxLayout()
        _layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        _layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(_layout)
        self._cbox = QtW.QComboBox()
        self._label = QtW.QLabel()
        _layout.addWidget(self._label)
        _layout.addWidget(self._cbox)

        self._cbox.currentIndexChanged.connect(self.currentIndexChanged.emit)

    def label(self) -> str:
        """Return the label text."""
        return self._label.text()

    def setLabel(self, text: str) -> None:
        """Set the text of label."""
        return self._label.setText(text)

    def choices(self) -> list[Any]:
        return list(map(str, self._values))

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

    def currentValue(self) -> Any:
        """Current value."""
        return self._values[self.currentIndex()]

    def setCurrentValue(self, value: Any) -> None:
        try:
            index = self._values.index(value)
        except ValueError:
            raise ValueError(f"{value} is not a valid choice.")
        return self.setCurrentIndex(index)

    def copy(self, link: bool = True):
        new = self.__class__()
        new.setLabel(self.label())
        new.setChoices(self.choices())
        new.setCurrentIndex(self.currentIndex())
        new.currentIndexChanged.connect(self.currentIndexChanged.emit)
        if link:
            new.currentIndexChanged.connect(self.setCurrentIndex)
            self.currentIndexChanged.connect(new.setCurrentIndex)

        return new


class _QGroupByWidget(QtW.QWidget):
    _groupby: QTableGroupBy | None = None
    _qtable_view: _QTableViewEnhanced | None = None

    @classmethod
    def from_groupby(cls, parent: QTableGroupBy) -> _QGroupByWidget:
        self = cls.from_widgets(parent._group_key_cbox, parent._qtable_view)
        self._groupby = parent
        return self

    @classmethod
    def from_widgets(cls, cbox: _QLabeledComboBox, table: _QTableViewEnhanced):
        self = cls()
        _main_layout = QtW.QVBoxLayout()
        _main_layout.setContentsMargins(0, 0, 0, 0)
        _main_layout.addWidget(cbox)
        _main_layout.addWidget(table)
        self.setLayout(_main_layout)
        self._qtable_view = table
        return self

    def copy(self, link: bool = True) -> _QGroupByWidget:
        groupby: QTableGroupBy = self._groupby
        new_cbox = groupby._group_key_cbox.copy(link=link)
        new_table = groupby._qtable_view.copy(link=link)
        new = self.__class__.from_widgets(new_cbox, new_table)
        new_table.setVisible(True)
        new._groupby = groupby
        return new

    @property
    def _selection_model(self):
        return self._groupby._qtable_view._selection_model

    @property
    def _on_moving(self):
        return self._groupby._qtable_view._on_moving

    @property
    def _on_moved(self):
        return self._groupby._qtable_view._on_moved


class QTableGroupBy(QBaseTable):
    _data_raw: DataFrameGroupBy

    @property
    def _qtable_view(self) -> _QTableViewEnhanced:
        return self._qtable_view_

    @property
    def _central_widget(self) -> _QGroupByWidget:
        return self._central_widget_

    def createQTableView(self):
        self._qtable_view_ = _QTableViewEnhanced(self)
        self._group_key_cbox = _QLabeledComboBox()
        self._group_map: dict[Hashable, Sequence[int]] = {}
        self._group_key_cbox.currentIndexChanged.connect(self._on_cbox_changed)
        wdt = _QGroupByWidget.from_groupby(self)
        self._central_widget_ = wdt
        self.addWidget(wdt)

    def _on_cbox_changed(self):
        return self.setProxy(self._proxy)

    def getDataFrame(self) -> DataFrameGroupBy:
        return self._data_raw

    @QBaseTable._mgr.interface
    def setDataFrame(self, data: DataFrameGroupBy) -> None:
        if data is None:
            self._data_raw = data
            self._group_key_cbox.setLabel("")

            self._group_map = {}
            self._group_key_cbox.setChoices([])
            self.setProxy(None)
            self._qtable_view.viewport().update()
            return

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
        self.setProxy(None)
        self._qtable_view.viewport().update()
        return

    @setDataFrame.server
    def setDataFrame(self, data) -> None:
        return arguments(getattr(self, "_data_raw", None))

    def createModel(self):
        model = DataFrameModel(self)
        self._qtable_view.setModel(model)
        return None

    def tableSlice(self) -> pd.DataFrame:
        df: pd.DataFrame = self._data_raw.obj
        sl = self._group_map[self._group_key_cbox.currentValue()]
        return df.iloc[sl, :]

    def currentGroup(self) -> Hashable:
        """Return the label of the current group."""
        index = self._group_key_cbox.currentIndex()
        return self._group_key_cbox._values[index]

    def setCurrentGroup(self, group: Hashable) -> None:
        return self._group_key_cbox.setCurrentValue(group)
