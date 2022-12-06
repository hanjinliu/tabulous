from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Hashable, TYPE_CHECKING, Mapping, Union
from psygnal import SignalGroup, Signal

from tabulous.widgets.filtering import FilterProxy
from tabulous.widgets._component import (
    CellInterface,
    HorizontalHeaderInterface,
    VerticalHeaderInterface,
    PlotInterface,
    ColumnDtypeInterface,
    CellReferenceInterface,
    SelectionRanges,
    HighlightRanges,
)
from tabulous.widgets import _doc
from tabulous.types import ItemInfo, HeaderInfo, EvalInfo
from tabulous._psygnal import SignalArray, InCellRangedSlot

if TYPE_CHECKING:
    from typing_extensions import Self
    import pandas as pd
    from collections_undo import UndoManager
    from qtpy import QtWidgets as QtW
    from magicgui.widgets import Widget

    from tabulous._qt import QTableLayer, QSpreadSheet, QTableGroupBy, QTableDisplay
    from tabulous._qt._table import QBaseTable
    from tabulous._qt._table._base._overlay import QOverlayFrame
    from tabulous._qt._keymap import QtKeyMap

    from tabulous.color import ColorType

    ColorMapping = Union[Callable[[Any], ColorType], Mapping[Hashable, ColorType]]
    Formatter = Union[Callable[[Any], str], str, None]
    Validator = Callable[[Any], None]

_Void = object()


class TableSignals(SignalGroup):
    """Signal group for a Table."""

    data = SignalArray(ItemInfo)
    index = Signal(HeaderInfo)
    columns = Signal(HeaderInfo)
    evaluated = Signal(EvalInfo)
    selections = Signal(SelectionRanges)
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
#   The abstract base class of tables.
# #####################################################################


class TableBase(ABC):
    """The base class for a table layer."""

    _Default_Name = "None"
    cell = CellInterface()
    index = VerticalHeaderInterface()
    columns = HorizontalHeaderInterface()
    plt = PlotInterface()
    cellref = CellReferenceInterface()
    filter = FilterProxy()
    selections = SelectionRanges()
    highlights = HighlightRanges()

    def __init__(
        self,
        data: Any = None,
        name: str | None = None,
        editable: bool = True,
        metadata: dict[str, Any] | None = None,
    ):
        _data = self._normalize_data(data)

        if name is None:
            name = self._Default_Name
        self.events = TableSignals()
        self._name = str(name)
        self._qwidget = self._create_backend(_data)
        self._qwidget.connectSelectionChangedSignal(self._emit_selections)
        self._qwidget._qtable_view._table_map.set.connect(
            lambda k, v: self.events.data.connect_cell_slot(v)
        )
        self._qwidget._qtable_view._table_map.deleted.connect(
            self.events.data.disconnect
        )
        self._view_mode = ViewMode.normal
        self._metadata: dict[str, Any] = metadata or {}

        if self.mutable:
            with self._qwidget._mgr.blocked():
                self._qwidget.setEditable(editable)
            self._qwidget.connectItemChangedSignal(
                self._emit_data_changed_signal,
                self.events.index.emit,
                self.events.columns.emit,
                self.events.evaluated.emit,
            )

            self.events.evaluated.connect(self._emit_evaluated)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}<{self.name!r}>"

    def _emit_data_changed_signal(self, info: ItemInfo) -> None:
        r, c = info.row, info.column
        if info.value is info.DELETED or info.old_value is info.INSERTED:
            # insertion/deletion emits signal from the next row/column.
            _is_deleted = info.value is info.DELETED
            if r == slice(None):
                # column is deleted/inserted
                if isinstance(c, slice):
                    index, count = c.start, c.stop - c.start
                else:
                    index, count = c, 1
                if _is_deleted:
                    self.events.data.remove_columns(index, count)
                else:
                    self.events.data.insert_columns(index, count)
                self.events.data[:, c.start :].emit(info)
            else:
                # row is deleted/inserted
                if isinstance(r, slice):
                    index, count = r.start, r.stop - r.start
                else:
                    index, count = r, 1
                if _is_deleted:
                    self.events.data.remove_rows(index, count)
                else:
                    self.events.data.insert_rows(index, count)
                self.events.data[r.start :, :].emit(info)
        else:
            self.events.data[r, c].emit(info)

    @abstractmethod
    def _create_backend(self, data: pd.DataFrame) -> QBaseTable:
        """This function creates a backend widget."""

    @abstractmethod
    def _normalize_data(self, data):
        """Data normalization before setting a new data."""

    @property
    def table_type(self) -> str:
        """Return the table type in string."""
        return type(self).__name__

    @property
    def data(self) -> pd.DataFrame:
        """Table data."""
        return self._qwidget.getDataFrame()

    @data.setter
    def data(self, value):
        """Set table data."""
        _data = self._normalize_data(value)
        self._qwidget.setDataFrame(_data)

    @property
    def data_shown(self) -> pd.DataFrame:
        """Return the data shown in the table (filter considered)."""
        return self._qwidget.dataShown(parse=True)

    @property
    def mutable(self) -> bool:
        """Mutability of the table."""
        from tabulous._qt._table import QMutableTable

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
    def metadata(self) -> dict[str, Any]:
        """Metadata of the table."""
        return self._metadata

    @metadata.setter
    def metadata(self, value: dict[str, Any]) -> None:
        """Set metadata of the table."""
        if not isinstance(value, dict):
            raise TypeError("metadata must be a dict")
        self._metadata = value

    @property
    def zoom(self) -> float:
        """Zoom factor of table."""
        return self._qwidget.zoom()

    @zoom.setter
    def zoom(self, value: float):
        """Set zoom factor of table."""
        return self._qwidget.setZoom(value)

    @property
    def name(self) -> str:
        """Table name."""
        return self._name

    @name.setter
    def name(self, value: str):
        """Set table name."""
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
        """Set editability of table."""
        if self.mutable:
            self._qwidget.setEditable(value)
        elif value:
            raise ValueError("Table is not mutable.")

    @property
    def native(self) -> QBaseTable:
        """The backend widget."""
        return self._qwidget

    # TODO: def drop(self, labels: list[str]) -> Self:

    def refresh(self) -> None:
        """Refresh the table view and force table to update."""
        return self._qwidget.refreshTable(process=True)

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
        colormap: ColorMapping | None = _Void,
    ):
        """
        Set foreground color rule.

        Parameters
        ----------
        column_name : Hashable
            Target column name.
        colormap : callable or None, optional
            Colormap function. Must return a color-like object. Pass None to reset
            the colormap.
        """

        def _wrapper(f: ColorMapping) -> ColorMapping:
            self._qwidget.setForegroundColormap(column_name, f)
            return f

        if isinstance(colormap, Mapping):
            return _wrapper(lambda x: colormap.get(x, None))
        elif colormap is _Void:
            return _wrapper
        else:
            return _wrapper(colormap)

    def background_colormap(
        self,
        column_name: Hashable,
        /,
        colormap: ColorMapping | None = _Void,
    ):
        """
        Set background color rule.

        Parameters
        ----------
        column_name : Hashable
            Target column name.
        colormap : callable or None, optional
            Colormap function. Must return a color-like object. Pass None to reset
            the colormap.
        """

        def _wrapper(f: ColorMapping) -> ColorMapping:
            self._qwidget.setBackgroundColormap(column_name, f)
            return f

        if isinstance(colormap, Mapping):
            return _wrapper(lambda x: colormap.get(x, None))
        elif colormap is _Void:
            return _wrapper
        else:
            return _wrapper(colormap)

    def formatter(
        self,
        column_name: Hashable,
        /,
        formatter: Formatter | None = _Void,
    ):
        """
        Set column specific text formatter.

        Parameters
        ----------
        column_name : Hashable
            Target column name.
        formatter : callable, optional
            Formatter function. Pass None to reset the formatter.
        """

        def _wrapper(f: Formatter) -> Formatter:
            self._qwidget.setTextFormatter(column_name, f)
            return f

        return _wrapper(formatter) if formatter is not _Void else _wrapper

    text_formatter = formatter  # alias

    def validator(
        self,
        column_name: Hashable,
        /,
        validator: Validator | None = _Void,
    ):
        """
        Set column specific data validator.

        Parameters
        ----------
        column_name : Hashable
            Target column name.
        validator : callable or None, optional
            Validator function. Pass None to reset the validator.
        """

        def _wrapper(f: Validator) -> Validator:
            self._qwidget.setDataValidator(column_name, f)
            return f

        return _wrapper(validator) if validator is not _Void else _wrapper

    @property
    def view_mode(self) -> ViewMode:
        """View mode of the table."""
        return self._view_mode

    @view_mode.setter
    def view_mode(self, mode) -> None:
        """Set view mode of the table."""
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
                self._qwidget._qtable_view.setFocus()

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

    def add_side_widget(self, widget: QtW.QWidget | Widget, *, name: str = ""):
        """
        Add a side widget to the table.

        A side widget is a widget that is docked to the side area of the table.
        It is visible only when the table is active. Thus, it is a good place
        to add a widget specific to the table.

        Parameters
        ----------
        widget: QWidget or magicgui Widget
            The widget to add.
        name : str, optional
            Name of the size widget. Use the input widget name by default.
        """
        if hasattr(widget, "native"):
            name = name or widget.name
            widget = widget.native
        else:
            name = name or widget.objectName()

        self._qwidget.addSideWidget(widget, name=name)
        return widget

    def add_overlay_widget(
        self,
        widget: QtW.QWidget | Widget,
        *,
        label: str = "",
        topleft: tuple[float, float] = (0, 0),
        size: tuple[float, float] | None = None,
        grip: bool = True,
    ) -> QOverlayFrame:
        """
        Add a widget overlaid over the table.

        An overlay widget is shown on top of the table, just like the chart in Excel.

        Parameters
        ----------
        widget: QWidget or magicgui Widget
            The widget to add.
        label : str, optional
            Label that is shown in the bottom of the widget.
        topleft: tuple of float, optional
            Top-left position of the widget described as the row and column indices.
        """
        if hasattr(widget, "native"):
            widget = widget.native

        return self._qwidget.addOverlayWidget(
            widget,
            label=label,
            topleft=topleft,
            size=size,
            grip=grip,
        )

    def _emit_selections(self):
        with self.selections.blocked():
            # Block selection to avoid recursive update.
            self.events.selections.emit(self.selections)
        return None

    def _emit_evaluated(self, info: EvalInfo):
        if info.expr == "":
            return None

        pos = (info.row, info.column)
        # literal_callable = LiteralCallable.from_table(self, info.expr, pos)
        qtable = self.native
        qtable_view = qtable._qtable_view

        # slot = self.events.data.connect_expr(self, info.expr, pos)
        slot = InCellRangedSlot.from_table(self, info.expr, pos)

        def _raise(e):
            # the common exception handling
            if not isinstance(e, (SyntaxError, AttributeError)):
                # Update cell text with the exception object.
                try:
                    del qtable_view._focused_widget
                except RuntimeError:
                    pass
                with qtable_view._selection_model.blocked():
                    qtable.setDataFrameValue(*pos, "#ERROR")
                return None
            # SyntaxError/AttributeError might be caused by mistouching. Don't close
            # the editor.
            e.args = (f"{str(e)}\n>>> {info.expr}",)
            raise e

        if not info.is_ref:
            result = slot.evaluate()
            if e := result.get_err():
                _raise(e)
            else:
                self.move_iloc(*pos)
        else:
            if next(iter(slot.range), None) is None:
                # if no reference exists, evaluate the expression as "=..." form.
                return self._emit_evaluated(EvalInfo(*pos, info.expr, False))
            with qtable._mgr.merging(formatter=lambda cmds: cmds[-1].format()):
                # call here to properly update undo stack
                result = slot.evaluate()
                if e := result.get_err():
                    _raise(e)
                qtable.setCalculationGraph(pos, slot)

        # if not info.is_ref:
        #     # evaluated by "=..."
        #     result = literal_callable(unblock=True)  # cells updated here if succeeded
        #     if e := result.get_err():
        #         _raise(e)
        #     else:
        #         self.move_iloc(*pos)
        # else:
        #     # evaluated by "&=..."
        #     selections = literal_callable.selection_ops
        #     if len(selections) == 0:
        #         # if no reference exists, evaluate the expression as "=..." form.
        #         return self._emit_evaluated(EvalInfo(*pos, info.expr, False))
        #     graph = Graph(self, literal_callable, selections)
        #     with qtable._mgr.merging(formatter=lambda cmds: cmds[-1].format()):
        #         # call here to properly update undo stack
        #         result = literal_callable(unblock=True)
        #         if e := result.get_err():
        #             _raise(e)
        #         with graph.blocked():
        #             qtable.setCalculationGraph(pos, graph)

        del qtable_view._focused_widget
        return None


# #############################################################################
#   Concrete table widgets
# #############################################################################


class _DataFrameTableLayer(TableBase):
    """Table layer for DataFrame."""

    _qwidget: QTableLayer | QSpreadSheet

    def _normalize_data(self, data) -> pd.DataFrame:
        import pandas as pd

        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)
        return data

    def assign(self, other: dict[str, Any] = {}, **kwargs: dict[str, Any]) -> Self:
        """
        Assign new column(s) to the table.

        Examples
        --------
        >>> table.assign(a=[1, 2, 3], b=[2, 3, 4])
        >>> table.assign({"a": [1, 2, 3], "b": [2, 3, 4]})

        Returns
        -------
        TableBase
            Same table object with new columns.
        """
        import pandas as pd

        kwargs = dict(**other, **kwargs)
        if self._qwidget._data_raw.size == 0:
            # DataFrame.assign does not support updating empty DataFrame.
            self._qwidget.setDataFrame(pd.DataFrame(kwargs))
        else:
            serieses: dict[str, pd.Series] = {}
            for k, v in kwargs.items():
                serieses[str(k)] = pd.Series(v, index=self.data.index, name=k)

            self._qwidget.assignColumns(serieses)
        return self


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
        from tabulous._qt import QTableLayer

        return QTableLayer(data=data)


@_doc.update_doc
class SpreadSheet(_DataFrameTableLayer):
    """
    A table that behaves like a spreadsheet.

    Parameters
    ----------
    data : DataFrame like, optional
        Table data to add.
    {name}{editable}{metadata}
    """

    _qwidget: QSpreadSheet
    _Default_Name = "sheet"
    dtypes = ColumnDtypeInterface()

    def _create_backend(self, data: pd.DataFrame) -> QSpreadSheet:
        from tabulous._qt import QSpreadSheet

        return QSpreadSheet(data=data)

    def add_item_widget(self, row: int, column: int, widget):
        """Add a widget to a cell."""
        return self._qwidget._set_widget_at_index(row, column, widget)


@_doc.update_doc
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
        from tabulous._qt import QTableGroupBy

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


@_doc.update_doc
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
        from tabulous._qt import QTableDisplay

        return QTableDisplay(loader=data)

    def _normalize_data(self, data):
        if not callable(data):
            raise TypeError("Can only add callable object.")
        return data

    @property
    def interval(self) -> int:
        """Interval of table refresh."""
        return self._qwidget.interval()

    @interval.setter
    def interval(self, value: int) -> None:
        """Set the interval of table refresh."""
        if not 10 <= value <= 10000:
            raise ValueError("Interval must be between 10 and 10000.")
        self._qwidget.setInterval(value)

    @property
    def loader(self) -> Callable[[], Any]:
        """Loader function."""
        return self._qwidget.loader()

    @loader.setter
    def loader(self, value: Callable[[], Any]) -> None:
        self._qwidget.setLoader(value)

    @property
    def running(self) -> bool:
        """True if the loading task is running"""
        return self._qwidget.running()

    @running.setter
    def running(self, value: bool) -> None:
        return self._qwidget.setRunning(value)
