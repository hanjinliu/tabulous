from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Callable, TYPE_CHECKING
from functools import partial
from psygnal import SignalGroup, Signal

from .keybindings import register_shortcut
from .filtering import FilterProxy

from ..types import (
    SelectionRanges,
    ItemInfo,
    HeaderInfo,
    SelectionType,
    _SingleSelection,
)

if TYPE_CHECKING:
    import pandas as pd
    from collections_undo import UndoManager
    from .._qt import QTableLayer, QSpreadSheet, QTableGroupBy, QTableDisplay
    from .._qt._table import QBaseTable


class TableSignals(SignalGroup):
    """Signal group for a Table."""

    data = Signal(ItemInfo)
    index = Signal(HeaderInfo)
    columns = Signal(HeaderInfo)
    selections = Signal(object)
    zoom = Signal(float)
    renamed = Signal(str)


class TableBase(ABC):
    """The base class for a table layer."""

    _Default_Name = "None"

    def __init__(self, data, name=None, editable: bool = True):
        self._data = self._normalize_data(data)
        from .._qt._table import QMutableTable

        if name is None:
            name = self._Default_Name
        self.events = TableSignals()
        self._name = str(name)
        self._qwidget = self._create_backend(self._data)
        self._qwidget.connectSelectionChangedSignal(self.events.selections.emit)

        if isinstance(self._qwidget, QMutableTable):
            self._qwidget.setEditable(editable)
            self._qwidget.connectItemChangedSignal(
                self.events.data.emit,
                self.events.index.emit,
                self.events.columns.emit,
            )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}<{self.name!r}>"

    @abstractmethod
    def _create_backend(self, data: pd.DataFrame) -> QBaseTable:
        """This function creates a backend widget."""

    @abstractmethod
    def _normalize_data(self, data):
        """Data normalization before setting a new data."""

    @property
    def data(self) -> pd.DataFrame:
        """Table data."""
        return self._qwidget.getDataFrame()

    @data.setter
    def data(self, value):
        self._data = self._normalize_data(value)
        self._qwidget.setDataFrame(self._data)

    @property
    def table_shape(self) -> tuple[int, int]:
        """Shape of table."""
        return self._qwidget.tableShape()

    @property
    def precision(self) -> int:
        """Precision (displayed digits) of table."""
        return self._qwidget.precision()

    @precision.setter
    def precision(self, value: int) -> None:
        self._qwidget.setPrecision(value)

    @property
    def zoom(self) -> float:
        """Zoom factor of table."""
        return self._qwidget.zoom()

    @zoom.setter
    def zoom(self, value: float):
        self._qwidget.setZoom(value)

    def _set_name(self, value: str):
        with self.events.renamed.blocked():
            self.name = value

    @property
    def name(self) -> str:
        """Table name."""
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = str(value)
        self.events.renamed.emit(self._name)

    @property
    def editable(self) -> bool:
        """Editability of table."""
        return self._qwidget.isEditable()

    @editable.setter
    def editable(self, value: bool):
        self._qwidget.setEditable(value)

    @property
    def selections(self):
        """Get the SelectionRanges object of current table selection."""
        rngs = SelectionRanges(self._qwidget.selections())
        rngs._changed.connect(self._qwidget.setSelections)
        rngs.events.removed.connect(lambda i, value: self._qwidget.setSelections(rngs))
        return rngs

    @selections.setter
    def selections(self, value: SelectionType | _SingleSelection) -> None:
        if not isinstance(value, list):
            value = [value]
        self._qwidget.setSelections(value)

    def refresh(self) -> None:
        """Refresh the table view."""
        return self._qwidget.refresh()

    filter = FilterProxy()

    @property
    def undo_manager(self) -> UndoManager:
        """Return the undo manager."""
        return self._qwidget._mgr

    def bind_key(self, *seq) -> Callable[[TableBase], Any | None]:
        """Bind callback function to a key sequence."""

        def register(f):
            register_shortcut(seq, self._qwidget, partial(f, self))

        return register


class _DataFrameTableLayer(TableBase):
    """Table layer for DataFrame."""

    def _normalize_data(self, data) -> pd.DataFrame:
        import pandas as pd

        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)
        return data


class Table(_DataFrameTableLayer):
    _Default_Name = "table"

    def _create_backend(self, data: pd.DataFrame) -> QTableLayer:
        from .._qt import QTableLayer

        return QTableLayer(data=data)


class SpreadSheet(_DataFrameTableLayer):
    _Default_Name = "sheet"

    def _create_backend(self, data: pd.DataFrame) -> QSpreadSheet:
        from .._qt import QSpreadSheet

        return QSpreadSheet(data=data)


class GroupBy(TableBase):
    _Default_Name = "groupby"

    def _create_backend(self, data: pd.DataFrame) -> QTableGroupBy:
        from .._qt import QTableGroupBy

        return QTableGroupBy(data=data)

    def _normalize_data(self, data):
        import pandas as pd
        from pandas.core.groupby.generic import DataFrameGroupBy

        if isinstance(data, DataFrameGroupBy):
            pass
        elif isinstance(data, (list, tuple, dict)):
            data_all = []
            group = "group"
            if isinstance(data, dict):
                it = data.items()
            else:
                it = enumerate(data)
            for key, df in it:
                df = pd.DataFrame(df)
                if group in df.columns:
                    raise ValueError("Input data must not have a 'group' column.")
                data_all.append(df.assign(group=key))
            data = pd.concat(data_all, axis=0).groupby(group)
        else:
            raise TypeError("Cannot only add DataFrameGroupBy object.")
        return data

    @property
    def current_group(self):
        """Current group ID."""
        return self._qwidget.currentGroup()

    @current_group.setter
    def current_group(self, val) -> None:
        return self._qwidget.setCurrentGroup(val)


class TableDisplay(TableBase):
    _Default_Name = "display"

    def _create_backend(self, data: Callable[[], Any]) -> QTableDisplay:
        from .._qt import QTableDisplay

        return QTableDisplay(loader=data)

    def _normalize_data(self, data):
        if not callable(data):
            raise TypeError("Can only add callable object.")
        return data

    @property
    def interval(self) -> int:
        """Interval of table refresh."""
        return self._qwidget._qtimer.interval()

    @interval.setter
    def interval(self, value: int) -> None:
        if not 10 <= value <= 10000:
            raise ValueError("Interval must be between 10 and 10000.")
        self._qwidget._qtimer.setInterval(value)

    @property
    def loader(self) -> Callable[[], Any]:
        """Loader function."""
        return self._qwidget.loader()

    @loader.setter
    def loader(self, value: Callable[[], Any]) -> None:
        self._qwidget.setLoader(value)
