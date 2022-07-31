from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING
from psygnal import SignalGroup, Signal

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
    from qtpy import QtWidgets as QtW
    from magicgui.widgets import Widget

    from .._qt import QTableLayer, QSpreadSheet, QTableGroupBy, QTableDisplay
    from .._qt._table import QBaseTable
    from .._qt._keymap import QtKeyMap


class TableSignals(SignalGroup):
    """Signal group for a Table."""

    data = Signal(ItemInfo)
    index = Signal(HeaderInfo)
    columns = Signal(HeaderInfo)
    selections = Signal(object)
    zoom = Signal(float)
    renamed = Signal(str)


class ViewMode(Enum):
    normal = "normal"
    horizontal = "horizontal"
    vertical = "vertical"
    popup = "popup"

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        return super().__eq__(other)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}.{self.name}>"


class TableBase(ABC):
    """The base class for a table layer."""

    _Default_Name = "None"

    def __init__(self, data, name=None, editable: bool = True):
        self._data = self._normalize_data(data)

        if name is None:
            name = self._Default_Name
        self.events = TableSignals()
        self._name = str(name)
        self._qwidget = self._create_backend(self._data)
        self._qwidget.connectSelectionChangedSignal(self.events.selections.emit)
        self._view_mode = ViewMode.normal

        if self.mutable:
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
    def mutable(self) -> bool:
        """Mutability of the table."""
        from .._qt._table import QMutableTable

        return isinstance(self._qwidget, QMutableTable)

    @property
    def table_shape(self) -> tuple[int, int]:
        """Shape of table."""
        return self._qwidget.tableShape()

    @property
    def keymap(self) -> QtKeyMap:
        return self._qwidget._keymap

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
        if self.mutable:
            return self._qwidget.isEditable()
        else:
            return False

    @editable.setter
    def editable(self, value: bool):
        if self.mutable:
            self._qwidget.setEditable(value)
        elif value:
            raise ValueError("Table is not mutable.")

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

    def move_loc(self, row: Any, column: Any):
        """Move to a location in the table using axis label."""
        data = self.data
        r = data.index.get_loc(row)
        c = data.columns.get_loc(column)
        return self._qwidget.moveToItem(r, c)

    def move_iloc(self, row: int, column: int):
        """Move to a location in the table using indices."""
        shape = self.table_shape
        row_outofrange = row >= shape[0]
        col_outofrange = column >= shape[1]
        if row_outofrange or col_outofrange:
            raise IndexError(
                f"Indices {(row, column)!r} out of range of table shape {shape!r}."
            )
        return self._qwidget.moveToItem(row, column)

    @property
    def view_mode(self) -> str:
        """View mode of the table."""
        return self._view_mode

    @view_mode.setter
    def view_mode(self, mode) -> None:
        if mode is None:
            mode = ViewMode.normal
        else:
            mode = ViewMode(mode)

        if mode in (ViewMode.horizontal, ViewMode.vertical):
            self._qwidget.setDualView(orientation=mode.name)
        elif mode == ViewMode.popup:
            view = self._qwidget.setPopupView()
            view.popup.setTitle(self.name)

            @view.popup.closed.connect
            def _():
                self.view_mode = ViewMode.normal

        elif mode == ViewMode.normal:
            self._qwidget.resetViewMode()
        else:
            raise ValueError(f"Unknown view mode: {mode!r}.")

        self._view_mode = mode
        return None

    filter = FilterProxy()

    @property
    def undo_manager(self) -> UndoManager:
        """Return the undo manager."""
        return self._qwidget._mgr

    def add_side_widget(self, wdt: QtW.QWidget | Widget):
        if hasattr(wdt, "native"):
            wdt = wdt.native
        self._qwidget.addSideWidget(wdt)
        return wdt


class _DataFrameTableLayer(TableBase):
    """Table layer for DataFrame."""

    def _normalize_data(self, data) -> pd.DataFrame:
        import pandas as pd

        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)
        return data


class Table(_DataFrameTableLayer):
    _Default_Name = "table"
    _qwidget: QTableLayer

    def _create_backend(self, data: pd.DataFrame) -> QTableLayer:
        from .._qt import QTableLayer

        return QTableLayer(data=data)


class SpreadSheet(_DataFrameTableLayer):
    _Default_Name = "sheet"
    _qwidget: QSpreadSheet

    def _create_backend(self, data: pd.DataFrame) -> QSpreadSheet:
        from .._qt import QSpreadSheet

        return QSpreadSheet(data=data)


class GroupBy(TableBase):
    _Default_Name = "groupby"
    _qwidget: QTableGroupBy

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
    _qwidget: QTableDisplay

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
