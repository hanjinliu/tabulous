from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING, Hashable
from psygnal import SignalGroup, Signal

from .filtering import FilterProxy
from ._component import Component
from . import _doc

from ..exceptions import TableImmutableError
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

    from ..color import ColorType

    ColorMapping = Callable[[Any], ColorType]


class TableSignals(SignalGroup):
    """Signal group for a Table."""

    data = Signal(ItemInfo)
    index = Signal(HeaderInfo)
    columns = Signal(HeaderInfo)
    selections = Signal(SelectionRanges)
    zoom = Signal(float)
    renamed = Signal(str)


class ViewMode(Enum):
    """Enum of view modes"""

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


# #####################################################################
#   Table interfaces
# #####################################################################


class CellInterface(Component["TableBase"]):
    """The interface for editing cell as if it was manually edited."""

    def __getitem__(self, key: tuple[int | slice, int | slice]):
        return self.parent._qwidget.model().df.iloc[key]

    def __setitem__(self, key: tuple[int | slice, int | slice], value: Any) -> None:
        table = self.parent
        if not table.editable:
            raise TableImmutableError("Table is not editable.")
        import pandas as pd

        if isinstance(value, str) or not hasattr(value, "__iter__"):
            _value = [[value]]
        else:
            _value = value
        try:
            df = pd.DataFrame(_value)
        except ValueError:
            raise ValueError(f"Could not convert value {_value!r} to DataFrame.")
        row, col = self._normalize_key(key)

        if 1 in df.shape and (col.stop - col.start, row.stop - row.start) == df.shape:
            # it is natural to set an 1-D array without thinking of the direction.
            df = df.T

        table._qwidget.setDataFrameValue(row, col, df)

    def __delitem__(self, key: tuple[int | slice, int | slice]) -> None:
        """Deleting cell, equivalent to pushing Delete key."""

        table = self.parent
        if not table.editable:
            raise TableImmutableError("Table is not editable.")
        row, col = key
        table._qwidget.setSelections([(row, col)])
        table._qwidget.deleteValues()
        return None

    def _normalize_key(
        self,
        key: tuple[int | slice, int | slice],
    ) -> tuple[slice, slice]:
        if len(key) == 1:
            key = (key, slice(None))
        row, col = key
        _row_is_slice = isinstance(row, slice)
        _col_is_slice = isinstance(col, slice)
        if _row_is_slice:
            row = slice(*row.indices(self.parent.table_shape[0]))
            if row.step != 1:
                raise ValueError("Row slice step must be 1.")
        else:
            row = slice(row, row + 1)
        if _col_is_slice:
            col = slice(*col.indices(self.parent.table_shape[1]))
            if col.step != 1:
                raise ValueError("Column slice step must be 1.")
        else:
            col = slice(col, col + 1)
        return row, col


class PlotInterface(Component["TableBase"]):
    """The interface of plotting."""

    def __init__(self, parent=Component._no_ref):
        super().__init__(parent)
        self._current_widget = None

    def gcf(self):
        """Get current figure."""
        if self._current_widget is None:
            self.new_widget()
        return self._current_widget.figure

    def gca(self):
        """Get current axis."""
        if self._current_widget is None:
            self.new_widget()
        return self._current_widget.ax

    def new_widget(self, nrows=1, ncols=1):
        """Create a new plot widget and add it to the table."""
        from .._qt._plot import QtMplPlotCanvas

        table = self.parent
        if table._qwidget._qtable_view.parentViewer()._white_background:
            style = None
        else:
            style = "dark_background"
        wdt = QtMplPlotCanvas(nrows=nrows, ncols=ncols, style=style)
        wdt.canvas.deleteRequested.connect(self.delete_widget)
        table.add_side_widget(wdt, name="Plot")
        self._current_widget = wdt
        return wdt

    def delete_widget(self) -> None:
        """Delete the current widget from the side area."""
        if self._current_widget is None:
            return None
        try:
            self.parent._qwidget._side_area.removeWidget(self._current_widget)
        except Exception:
            pass
        self._current_widget.deleteLater()
        self._current_widget = None
        return None

    def figure(self, style=None):
        return self.subplots(style=style)[0]

    def subplots(self, nrows=1, ncols=1, style=None):
        wdt = self.new_widget(nrows=nrows, ncols=ncols, style=style)
        return wdt.figure, wdt.axes

    def plot(self, *args, **kwargs):
        """Call ``plt.plot`` on the current side figure."""
        out = self.gca().plot(*args, **kwargs)
        self.draw()
        return out

    def scatter(self, *args, **kwargs):
        """Call ``plt.scatter`` on the current side figure."""
        out = self.gca().scatter(*args, **kwargs)
        self.draw()
        return out

    def hist(self, *args, **kwargs):
        """Call ``plt.hist`` on the current side figure."""
        out = self.gca().hist(*args, **kwargs)
        self.draw()
        return out

    def draw(self):
        """Update the current side figure."""
        return self._current_widget.draw()


# #####################################################################
#   The abstract base class of tables.
# #####################################################################


class TableBase(ABC):
    """The base class for a table layer."""

    _Default_Name = "None"
    cell = CellInterface()
    plt = PlotInterface()
    filter = FilterProxy()

    def __init__(
        self,
        data: Any = None,
        name: str | None = None,
        editable: bool = True,
        metadata: dict[str, Any] = None,
    ):
        self._data = self._normalize_data(data)

        if name is None:
            name = self._Default_Name
        self.events = TableSignals()
        self._name = str(name)
        self._qwidget = self._create_backend(self._data)
        self._qwidget.connectSelectionChangedSignal(self._emit_selections)
        self._view_mode = ViewMode.normal
        self._metadata: dict[str, Any] = metadata or {}

        if self.mutable:
            with self._qwidget._mgr.blocked():
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
    def data_shown(self) -> pd.DataFrame:
        """Return the data shown in the table (filter considered)."""
        return self._qwidget.dataShown()

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
        """The keymap object."""
        return self._qwidget._keymap

    @property
    def precision(self) -> int:
        """Precision (displayed digits) of table."""
        return self._qwidget.precision()

    @precision.setter
    def precision(self, value: int) -> None:
        return self._qwidget.setPrecision(value)

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata

    @metadata.setter
    def metadata(self, value: dict[str, Any]) -> None:
        if not isinstance(value, dict):
            raise TypeError("metadata must be a dict")
        self._metadata = value

    @property
    def zoom(self) -> float:
        """Zoom factor of table."""
        return self._qwidget.zoom()

    @zoom.setter
    def zoom(self, value: float):
        return self._qwidget.setZoom(value)

    @property
    def name(self) -> str:
        """Table name."""
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = str(value)
        return self.events.renamed.emit(self._name)

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
    def selections(self) -> SelectionRanges:
        """Get the SelectionRanges object of current table selection."""
        return SelectionRanges(self, self._qwidget.selections())

    @selections.setter
    def selections(self, value: SelectionType | _SingleSelection) -> None:
        if not isinstance(value, list):
            value = [value]
        return self._qwidget.setSelections(value)

    @property
    def native(self) -> QBaseTable:
        """The backend widget."""
        return self._qwidget

    def refresh(self) -> None:
        """Refresh the table view."""
        return self._qwidget.refreshTable()

    def move_loc(self, row: Hashable, column: Hashable):
        """
        Move to a location in the table using axis label.
        >>> table.move_loc("index-2", "column-4")
        """
        data = self.data
        r = data.index.get_loc(row)
        c = data.columns.get_loc(column)
        return self._qwidget.moveToItem(r, c)

    def move_iloc(self, row: int | None, column: int | None):
        """
        Move to a location in the table using indices.
        >>> table.move_iloc(2, 4)
        """
        shape = self.table_shape
        row_outofrange = False if row is None else row >= shape[0]
        col_outofrange = False if column is None else column >= shape[1]
        if row_outofrange or col_outofrange:
            raise IndexError(
                f"Indices {(row, column)!r} out of range of table shape {shape!r}."
            )
        return self._qwidget.moveToItem(row, column)

    def foreground_colormap(
        self,
        column_name: Hashable,
        /,
        colormap: ColorMapping | None = None,
    ):
        """
        Set foreground color rule.

        Parameters
        ----------
        column_name : Hashable
            Target column name.
        colormap : callable, optional
            colormap function. Must return a color-like object.
        """

        def _wrapper(f: ColorMapping) -> ColorMapping:
            model = self._qwidget.model()
            model._foreground_colormap[column_name] = f
            self.refresh()
            return f

        return _wrapper(colormap) if colormap is not None else _wrapper

    def background_colormap(
        self,
        column_name: Hashable,
        /,
        colormap: ColorMapping | None = None,
    ):
        """
        Set background color rule.

        Parameters
        ----------
        column_name : Hashable
            Target column name.
        colormap : callable, optional
            colormap function. Must return a color-like object.
        """

        def _wrapper(f: ColorMapping) -> ColorMapping:
            model = self._qwidget.model()
            model._background_colormap[column_name] = f
            self.refresh()
            return f

        return _wrapper(colormap) if colormap is not None else _wrapper

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

    @property
    def undo_manager(self) -> UndoManager:
        """Return the undo manager."""
        return self._qwidget._mgr

    def add_side_widget(self, wdt: QtW.QWidget | Widget, name: str = ""):
        """Add a side widget to the table."""
        if hasattr(wdt, "native"):
            name = name or wdt.name
            wdt = wdt.native
        else:
            name = name or wdt.objectName()

        self._qwidget.addSideWidget(wdt, name=name)
        return wdt

    def _emit_selections(self):
        return self.events.selections.emit(self.selections)


class _DataFrameTableLayer(TableBase):
    """Table layer for DataFrame."""

    def _normalize_data(self, data) -> pd.DataFrame:
        import pandas as pd

        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)
        return data


@_doc.update_doc
class Table(_DataFrameTableLayer):
    """
    A table implemented with type checking.

    Parameters
    ----------
    data : DataFrame like, optional
        Table data to add.
    {name}{editable}{metadata}
    """

    _Default_Name = "table"
    _qwidget: QTableLayer

    def _create_backend(self, data: pd.DataFrame) -> QTableLayer:
        from .._qt import QTableLayer

        return QTableLayer(data=data)


class SpreadSheet(_DataFrameTableLayer):
    """
    A table that behaves like a spreadsheet.

    Parameters
    ----------
    data : DataFrame like, optional
        Table data to add.
    {name}{editable}{metadata}
    """

    _Default_Name = "sheet"
    _qwidget: QSpreadSheet

    def _create_backend(self, data: pd.DataFrame) -> QSpreadSheet:
        from .._qt import QSpreadSheet

        return QSpreadSheet(data=data)


class GroupBy(TableBase):
    """
    A group of tables.

    Parameters
    ----------
    data : DataFrameGroupBy like, optional
        Groupby data to add.
    {name}{metadata}{update}
    """

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
                df = pd.DataFrame(df, copy=True)
                if group in df.columns:
                    raise ValueError("Input data must not have a 'group' column.")
                data_all.append(df.assign(group=key))
            data = pd.concat(data_all, axis=0, ignore_index=True).groupby(group)
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
    """
    A table that is hotly reloaded by the given function.

    Parameters
    ----------
    data : callable, optional
        The loader function.
    {name}{metadata}{update}
    """

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
