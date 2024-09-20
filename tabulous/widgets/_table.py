from __future__ import annotations

import logging
from abc import abstractmethod
import ast
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Hashable, TYPE_CHECKING, Mapping, overload
import weakref
from psygnal import SignalGroup, Signal

from tabulous.widgets import _doc, _component as _comp
from tabulous.widgets._keymap_abc import SupportKeyMap
from tabulous.widgets._source import Source
from tabulous.types import ItemInfo, EvalInfo
from tabulous._psygnal import SignalArray, InCellRangedSlot

if TYPE_CHECKING:
    from typing_extensions import Self, Literal
    import numpy as np
    import pandas as pd
    from collections_undo import UndoManager
    from qtpy import QtWidgets as QtW
    from magicgui.widgets import Widget

    from tabulous._qt import QTableLayer, QSpreadSheet, QTableGroupBy, QTableDisplay
    from tabulous._qt._table import QBaseTable
    from tabulous._qt._table._base._overlay import QOverlayFrame

    LayoutString = Literal["horizontal", "vertical"]

logger = logging.getLogger("tabulous")


class TableSignals(SignalGroup):
    """Signal group for a Table."""

    data = SignalArray(ItemInfo)
    evaluated = Signal(EvalInfo)
    selections = Signal(_comp.SelectionRanges)
    renamed = Signal(str)
    _table: weakref.ReferenceType[TableBase]


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
#   Property-like
# #####################################################################


class DataProperty:
    """Internal data of the table."""

    def __get__(self, instance: TableBase, owner=None) -> pd.DataFrame:
        if instance is None:
            raise AttributeError("Cannot access property without instance.")
        return instance._qwidget.getDataFrame()

    def __set__(self, instance: TableBase, value: Any):
        if instance is None:
            raise AttributeError("Cannot access property without instance.")
        _data = instance._normalize_data(value)
        instance._qwidget.setDataFrame(_data)


class MetadataProperty:
    """Metadata dictionary of the table."""

    def __get__(self, instance: TableBase, owner=None) -> dict[str, Any]:
        if instance is None:
            raise AttributeError("Cannot access property without instance.")
        return instance._metadata

    def __set__(self, instance: TableBase, value: dict[str, Any]):
        if instance is None:
            raise AttributeError("Cannot access property without instance.")
        if not isinstance(value, dict):
            raise TypeError("metadata must be a dict")
        instance._metadata = value


# #####################################################################
#   The abstract base class of tables.
# #####################################################################


class TableBase(SupportKeyMap):
    """The base class for a table layer."""

    _Default_Name = "None"

    cell = _comp.CellInterface()
    index = _comp.VerticalHeaderInterface()
    columns = _comp.HorizontalHeaderInterface()
    plt = _comp.PlotInterface()
    proxy = _comp.ProxyInterface()
    text_color = _comp.TextColormapInterface()
    background_color = _comp.BackgroundColormapInterface()
    formatter = _comp.TextFormatterInterface()
    validator = _comp.ValidatorInterface()
    selections = _comp.SelectionRanges()
    highlights = _comp.HighlightRanges()
    loc = _comp.TableLocIndexer()
    iloc = _comp.TableILocIndexer()

    def __init__(
        self,
        data: Any = None,
        name: str | None = None,
        editable: bool = True,
        metadata: dict[str, Any] | None = None,
    ):
        from tabulous._qt import get_app
        from tabulous._map_model import SlotRefMapping

        _ = get_app()

        _data = self._normalize_data(data)

        if name is None:
            name = self._Default_Name
        self.events = TableSignals()
        self.events._table = weakref.ref(self)
        self._name = str(name)
        self._qwidget = self._create_backend(_data)
        self._install_actions()
        self._qwidget.connectSelectionChangedSignal(self._emit_selections)

        self._qwidget._qtable_view._table_map = SlotRefMapping(self)
        self._view_mode = ViewMode.normal
        self._metadata: dict[str, Any] = metadata or {}
        self._source = Source()

        if self.mutable:
            with self._qwidget._mgr.blocked():
                self._qwidget.setEditable(editable)
            self.native.connectItemChangedSignal(
                self._emit_data_changed_signal,
                self.index.events.renamed.emit,
                self.columns.events.renamed.emit,
                self.events.evaluated.emit,
            )

            self.events.evaluated.connect(self._emit_evaluated)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}<{self.name!r}>"

    def _ipython_key_completions_(self):
        return [name for name in self.columns]

    # fmt: off
    @overload
    def __getitem__(self, key: str) -> _comp.TableSeries: ...
    @overload
    def __getitem__(self, key: list[str]) -> _comp.TableSubset: ...
    # fmt: on

    def __getitem__(self, key):
        if isinstance(key, str):
            return _comp.TableSeries(self, slice(None), key)
        elif isinstance(key, list):
            return _comp.TableSubset(self, slice(None), key)
        raise TypeError(f"Invalid key type: {type(key)}")

    @property
    def source(self) -> Source:
        """The source of the table."""
        return self._source

    @property
    def current_index(self) -> tuple[int, int]:
        """The current index of the table."""
        return self._qwidget._qtable_view._selection_model.current_index

    @current_index.setter
    def current_index(self, index: tuple[int, int]) -> None:
        r, c = index
        return self.move_iloc(r, c)

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

    @staticmethod
    @abstractmethod
    def _normalize_data(data):
        """Data normalization before setting a new data."""

    @property
    def table_type(self) -> str:
        """Return the table type in string."""
        return type(self).__name__

    data = DataProperty()
    metadata = MetadataProperty()

    @property
    def data_shown(self) -> pd.DataFrame:
        """Return the data shown in the table (filter considered)."""
        return self._qwidget.dataShown(parse=True)

    @property
    def mutable(self):
        """Mutability of the table type."""
        from tabulous._qt._table import QMutableTable

        return isinstance(self._qwidget, QMutableTable)

    @property
    def table_shape(self) -> tuple[int, int]:
        """Shape of table (filter considered)."""
        return self._qwidget.tableShape()

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

    def move_iloc(self, row: int | None, column: int | None, scroll: bool = True):
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
        self._qwidget.moveToItem(row, column)
        if scroll:
            qtable_view = self._qwidget._qtable_view
            index = qtable_view.model().index(row, column)
            qtable_view.scrollTo(index)
        return None

    text_formatter = formatter  # alias

    @property
    def view_mode(self) -> ViewMode:
        """View mode of the table."""
        return self._view_mode

    @view_mode.setter
    def view_mode(self, mode) -> None:
        """Set view mode of the table."""

        if self._qwidget.parentViewer() is None:
            raise ValueError(
                "Table is not attached to a viewer. Cannot change the view mode."
            )
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
    def layout(self) -> LayoutString:
        """Table layout."""
        if self._qwidget.orientation() == 0:
            return "vertical"
        elif self._qwidget.orientation() == 1:
            return "horizontal"
        else:
            raise ValueError("Unknown layout.")

    @layout.setter
    def layout(self, layout: LayoutString) -> None:
        """Set table layout."""
        if layout == "vertical":
            self._qwidget.setOrientation(0)
        elif layout == "horizontal":
            self._qwidget.setOrientation(1)
        else:
            raise ValueError(f"Unknown layout: {layout!r}.")

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

    def save(self, path: str | Path) -> None:
        """Save table data to the given path."""
        from tabulous._io import save_file

        path = Path(path)
        save_file(path, self.data)
        self._source = self.source.replace(path=path)
        return None

    def screenshot(self) -> np.ndarray:
        """Get screenshot of the widget."""
        return self._qwidget.screenshot()

    def save_screenshot(self, path: str):
        """Save screenshot of the widget."""
        from PIL import Image

        arr = self.screenshot()
        Image.fromarray(arr).save(path)
        return None

    def _emit_selections(self):
        with self.selections.blocked():
            # Block selection to avoid recursive update.
            self.events.selections.emit(self.selections)
            _smodel = self.native._qtable_view._selection_model
            if sel := list(_smodel.iter_row_selections()):
                self.index.events.selected.emit(sel)
            if sel := list(_smodel.iter_col_selections()):
                self.columns.events.selected.emit(sel)

        return None

    def _emit_evaluated(self, info: EvalInfo):
        if info.expr == "":
            return None

        qtable = self.native
        qtable_view = qtable._qtable_view

        slot = InCellRangedSlot.from_table(self, info.expr, info.pos)

        def _raise(e: Exception):
            # the common exception handling
            if not isinstance(e, (SyntaxError, AttributeError, NameError)):
                # Update cell text with the exception object.
                try:
                    del qtable_view._focused_widget
                except RuntimeError:
                    pass
                with qtable_view._selection_model.blocked():
                    qtable.setDataFrameValue(*info.pos, "#ERROR")
                return None
            # SyntaxError, AttributeError or NameError might be caused by
            # mistouching. Don't close the editor.
            e.args = (f"{str(e)}\n>>> {info.expr}",)
            raise e

        if not info.is_ref:
            result = slot.evaluate()
            if e := result.get_err():
                _raise(e)
            else:
                self.move_iloc(*info.pos)
        else:
            if next(iter(slot.range), None) is None:
                # if no reference exists, evaluate the expression as "=..." form.
                return self._emit_evaluated(
                    EvalInfo(info.pos, info.source_pos, info.expr, False)
                )
            with qtable._mgr.merging(formatter=lambda cmds: cmds[-1].format()):
                # call here to properly update undo stack
                result = slot.evaluate()
                if e := result.get_err():
                    _raise(e)
                qtable.setInCellSlot(info.source_pos, slot)

        del qtable_view._focused_widget
        return None

    def _wrap_command(self, cmd: Callable):
        def _f(*_):
            logger.debug(f"Command: {cmd.__module__.split('.')[-1]}.{cmd.__name__}")
            if _qviewer := self._qwidget.parentViewer():
                _viewer = _qviewer._table_viewer
            else:
                from tabulous.widgets._mainwindow import DummyViewer

                _viewer = DummyViewer(self)
            return cmd(_viewer)

        return _f

    def _install_actions(self):
        from tabulous import commands as cmds

        _wrap = self._wrap_command

        # fmt: off
        _hheader_register = self.columns.register
        _hheader_register("Color > Set text colormap", _wrap(cmds.column.set_text_colormap))  # noqa: E501
        _hheader_register("Color > Reset text colormap", _wrap(cmds.column.reset_text_colormap))  # noqa: E501
        _hheader_register("Color > Set opacity to text colormap", _wrap(cmds.column.set_text_colormap_opacity))  # noqa: E501
        self._qwidget._qtable_view.horizontalHeader().addSeparator("Color")
        _hheader_register("Color > Set background colormap", _wrap(cmds.column.set_background_colormap))  # noqa: E501
        _hheader_register("Color > Reset background colormap", _wrap(cmds.column.reset_background_colormap))  # noqa: E501
        _hheader_register("Color > Set opacity to background colormap", _wrap(cmds.column.set_background_colormap_opacity))  # noqa: E501

        _hheader_register("Formatter > Set text formatter", _wrap(cmds.column.set_text_formatter))  # noqa: E501
        _hheader_register("Formatter > Reset text formatter", _wrap(cmds.column.reset_text_formatter))  # noqa: E501
        self._qwidget._qtable_view.horizontalHeader().addSeparator()
        _hheader_register("Sort", _wrap(cmds.selection.sort_by_columns))
        _hheader_register("Filter", _wrap(cmds.selection.filter_by_columns))
        self._qwidget._qtable_view.horizontalHeader().addSeparator()

        _cell_register = self.cell.register
        _cell_register("Copy")(_wrap(cmds.selection.copy_data_tab_separated))
        _cell_register("Copy as ... > Tab separated text", _wrap(cmds.selection.copy_data_tab_separated))  # noqa: E501
        _cell_register("Copy as ... > Tab separated text with headers", _wrap(cmds.selection.copy_data_with_header_tab_separated))  # noqa: E501
        _cell_register("Copy as ... > Comma separated text", _wrap(cmds.selection.copy_data_comma_separated))  # noqa: E501
        _cell_register("Copy as ... > Comma separated text with headers", _wrap(cmds.selection.copy_data_with_header_comma_separated))  # noqa: E501
        self._qwidget.addSeparator("Copy as ...")
        _cell_register("Copy as ... > Markdown", _wrap(cmds.selection.copy_as_markdown))  # noqa: E501
        _cell_register("Copy as ... > reStructuredText grid table", _wrap(cmds.selection.copy_as_rst_grid))  # noqa: E501
        _cell_register("Copy as ... > reStructuredText simple table", _wrap(cmds.selection.copy_as_rst_simple))  # noqa: E501
        _cell_register("Copy as ... > Latex", _wrap(cmds.selection.copy_as_latex))
        _cell_register("Copy as ... > HTML", _wrap(cmds.selection.copy_as_html))
        _cell_register("Copy as ... > Literal", _wrap(cmds.selection.copy_as_literal))
        self._qwidget.addSeparator("Copy as ... ")
        _cell_register("Copy as ... > New table", _wrap(cmds.selection.copy_as_new_table))  # noqa: E501
        _cell_register("Copy as ... > New spreadsheet", _wrap(cmds.selection.copy_as_new_spreadsheet))  # noqa: E501
        _cell_register("Paste", _wrap(cmds.selection.paste_data_tab_separated))
        _cell_register("Paste from ... > Tab separated text", _wrap(cmds.selection.paste_data_tab_separated))  # noqa: E501
        _cell_register("Paste from ... > Comma separated text", _wrap(cmds.selection.paste_data_comma_separated))  # noqa: E501
        _cell_register("Paste from ... > numpy-style text", _wrap(cmds.selection.paste_data_from_numpy_string))  # noqa: E501
        _cell_register("Paste from ... > Markdown text", _wrap(cmds.selection.paste_data_from_markdown))  # noqa: E501
        self._qwidget.addSeparator()
        _cell_register("Sort in-place", _wrap(cmds.selection.sort_inplace))
        self._qwidget.addSeparator()
        _cell_register("Code ... > Data-changed signal", _wrap(cmds.selection.write_data_signal_in_console))  # noqa: E501
        _cell_register("Code ... > Get slice", _wrap(cmds.selection.write_slice_in_console))  # noqa: E501
        _cell_register("Add highlight", _wrap(cmds.selection.add_highlight))
        _cell_register("Delete highlight", _wrap(cmds.selection.delete_selected_highlight))  # noqa: E501
        self._qwidget.addSeparator()
        # fmt: on


# #############################################################################
#   Concrete table widgets
# #############################################################################


class _DataFrameTableLayer(TableBase):
    """Table layer for DataFrame."""

    _qwidget: QTableLayer | QSpreadSheet
    native: QTableLayer | QSpreadSheet

    @staticmethod
    def _normalize_data(data) -> pd.DataFrame:
        import pandas as pd

        if not isinstance(data, pd.DataFrame):
            if isinstance(data, (Mapping, pd.Series, list)):
                data = pd.DataFrame(data)
            if is_polars_data_frame(data):
                data = data.to_pandas()
            elif is_polars_series(data):
                data = pd.DataFrame(data.to_pandas())
            elif is_xarray_data_array(data):
                data = data.to_dataframe("val").reset_index()
            else:
                data = pd.DataFrame(data)
        return data

    def assign(self, other: dict[str, Any] = {}, /, **kwargs: dict[str, Any]) -> Self:
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

    def query(self, text: str):
        df = self.data.eval(text, inplace=False, global_dict={"df": self.data})
        parsed = ast.parse(text.replace("@", "")).body[0]
        if type(parsed) is not ast.Assign:
            self._qwidget.parentViewer()._table_viewer.add_table(df, name=self.name)
        else:
            obj = parsed.targets[0]
            if type(obj) is not ast.Name:
                raise ValueError("Only simple assignment is supported.")
            name = obj.id
            new_ds = df[name]
            self.assign({name: new_ds})
        return None

    def append(self, row: Any) -> Self:
        """Append a row to the table."""
        import pandas as pd
        from tabulous._pd_index import is_ranged

        columns = self.columns.data
        if isinstance(row, pd.Series):
            _df = row.to_frame().T
        elif isinstance(row, (Mapping, pd.DataFrame)):
            _df = pd.DataFrame(row, copy=False, index=[0])
        elif is_polars_data_frame(row):
            _df = pd.DataFrame(row)
        else:
            _df = pd.DataFrame([list(row)])
        if is_ranged(_df.columns):
            if _df.columns.size < columns.size:
                n_more = columns.size - _df.columns.size
                _df = pd.concat(
                    [_df, pd.DataFrame([[self.native.NaN] * n_more])],
                    axis=1,
                    columns=columns,
                    ignore_index=True,
                )
            elif _df.columns.size == columns.size:
                _df = _df.rename(columns=dict(zip(_df.columns, columns)))
            else:
                raise ValueError("Too many columns.")

        else:
            not_exist = _df.columns.difference(self.columns.data)
            if not_exist.size > 0:
                raise ValueError(f"Columns {list(not_exist)} does not exist.")
        if self.table_type == "SpreadSheet":
            with self._qwidget._anim_row.using_animation(False):
                self.native.insertRows(self.table_shape[0], 1, row)
        else:
            self._qwidget.setDataFrame(pd.concat([self.data, _df], axis=0))
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
    native: QTableLayer

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
    native: QSpreadSheet
    _Default_Name = "sheet"
    dtypes = _comp.ColumnDtypeInterface()

    def _create_backend(self, data: pd.DataFrame) -> QSpreadSheet:
        from tabulous._qt import QSpreadSheet

        return QSpreadSheet(data=data)

    def _install_actions(self):
        from tabulous import commands as cmds

        _wrap = self._wrap_command
        # fmt: off
        _vheader_register = self.index.register
        _vheader_register("Insert row above", _wrap(cmds.selection.insert_row_above))
        _vheader_register("Insert row below", _wrap(cmds.selection.insert_row_below))
        _vheader_register("Remove selected rows", _wrap(cmds.selection.remove_selected_rows))  # noqa: E501
        self._qwidget._qtable_view.verticalHeader().addSeparator()

        _hheader_register = self.columns.register
        _hheader_register("Insert column left", _wrap(cmds.selection.insert_column_left))  # noqa: E501
        _hheader_register("Insert column right", _wrap(cmds.selection.insert_column_right))  # noqa: E501
        _hheader_register("Remove selected columns", _wrap(cmds.selection.remove_selected_columns))  # noqa: E501
        self._qwidget._qtable_view.horizontalHeader().addSeparator()
        _hheader_register("Column dtype", _wrap(cmds.selection.set_column_dtype))
        self._qwidget._qtable_view.horizontalHeader().addSeparator()

        _cell_register = self._qwidget.registerAction
        _cell_register("Insert/Remove > Insert a row above", _wrap(cmds.selection.insert_row_above))  # noqa: E501
        _cell_register("Insert/Remove > Insert a row below", _wrap(cmds.selection.insert_row_below))  # noqa: E501
        _cell_register("Insert/Remove > Remove rows", _wrap(cmds.selection.remove_selected_rows))  # noqa: E501
        self._qwidget.addSeparator()
        _cell_register("Insert/Remove > Insert a column on the left", _wrap(cmds.selection.insert_column_left))  # noqa: E501
        _cell_register("Insert/Remove > Insert a column on the right", _wrap(cmds.selection.insert_column_right))  # noqa: E501
        _cell_register("Insert/Remove > Remove columns", _wrap(cmds.selection.remove_selected_columns))  # noqa: E501
        self._qwidget.addSeparator()

        super()._install_actions()

        # fmt: on
        return None


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
    native: QTableGroupBy

    def _create_backend(self, data: pd.DataFrame) -> QTableGroupBy:
        from tabulous._qt import QTableGroupBy

        return QTableGroupBy(data=data)

    @staticmethod
    def _normalize_data(data):
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
    native: QTableDisplay

    def _create_backend(self, data: Callable[[], Any]) -> QTableDisplay:
        from tabulous._qt import QTableDisplay

        return QTableDisplay(loader=data)

    @staticmethod
    def _normalize_data(data):
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


def is_polars_data_frame(data):
    if _get_module(data) == "polars":
        import polars as pl

        return isinstance(data, pl.DataFrame)
    return False


def is_polars_series(data):
    if _get_module(data) == "polars":
        import polars as pl

        return isinstance(data, pl.Series)
    return False


def is_xarray_data_array(data):
    if _get_module(data) == "xarray":
        import xarray as xr

        return isinstance(data, xr.DataArray)
    return False


def _get_module(data) -> str:
    try:
        mod = type(data).__module__.split(".", 1)[0]
    except AttributeError:
        mod = ""
    return mod
