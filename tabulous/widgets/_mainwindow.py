from __future__ import annotations

from abc import ABC, abstractproperty
from functools import partial
from pathlib import Path
from types import MappingProxyType
import warnings
import weakref
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Union
from psygnal import Signal, SignalGroup
from superqt.utils import thread_worker

from ._table import Table, SpreadSheet, GroupBy, TableDisplay
from ._tablelist import TableList
from ._sample import open_sample
from ._component import Toolbar, Console, CommandPalette
from ._source import Source
from . import _doc

from tabulous import _utils, _io
from tabulous.types import SelectionType, TabPosition, _TableLike, _SingleSelection
from tabulous.exceptions import UnreachableError
from tabulous.widgets._keymap_abc import SupportKeyMap

if TYPE_CHECKING:
    from tabulous.widgets._table import TableBase
    from tabulous._qt import QMainWindow, QMainWidget
    from tabulous._qt._dockwidget import QtDockWidget
    from tabulous._qt._mainwindow import _QtMainWidgetBase
    from tabulous._qt._mainwindow._namespace import Namespace
    from qtpy.QtWidgets import QWidget
    from magicgui.widgets import Widget
    import numpy as np
    import pandas as pd

PathLike = Union[str, Path, bytes]


class TableType(Enum):
    table = "table"
    spreadsheet = "spreadsheet"


class TableViewerSignal(SignalGroup):
    """Signal group for table viewer."""

    current_index = Signal(int)


class _AbstractViewer(ABC):
    @abstractproperty
    def current_table(self) -> TableBase | None:
        """Return the currently visible table."""

    @abstractproperty
    def current_index(self) -> int | None:
        """Return the index of currently visible table."""

    @abstractproperty
    def cell_namespace(self) -> Namespace:
        """Return the namespace of the cell editor."""

    @property
    def data(self) -> pd.DataFrame | None:
        """The data of the current table if exists."""
        table = self.current_table
        if table is None:
            return None
        return table.data

    @property
    def config(self) -> MappingProxyType:
        """Return the config info."""
        return _utils.get_config().as_immutable()

    def reset_choices(self, *_):
        pass

    def copy_data(
        self,
        selections: SelectionType | _SingleSelection | None = None,
        *,
        headers: bool = False,
        sep: str = "\t",
    ) -> None:
        """Copy selected cells to clipboard."""
        if selections is not None:
            self.current_table.selections = selections
        return self.current_table._qwidget.copyToClipboard(headers=headers, sep=sep)

    def paste_data(
        self,
        selections: SelectionType | _SingleSelection | None = None,
    ) -> None:
        """Paste from clipboard."""
        if selections is not None:
            self.current_table.selections = selections
        return self.current_table._qwidget.pasteFromClipBoard()


class TableViewerBase(_AbstractViewer, SupportKeyMap):
    """The base class of a table viewer widget."""

    events: TableViewerSignal
    _qwidget_class: type[_QtMainWidgetBase]

    toolbar = Toolbar()
    console = Console()
    command_palette = CommandPalette()

    def __init__(
        self,
        *,
        tab_position: TabPosition | str = TabPosition.top,
        show: bool = True,
    ):
        from tabulous._qt import get_app
        from tabulous._utils import get_post_initializers

        app = get_app()  # noqa: F841
        self._qwidget = self._qwidget_class(tab_position=tab_position)
        self._qwidget._table_viewer = self
        self._tablist = TableList(parent=self)
        self._link_events()

        self.events = TableViewerSignal()
        self._table_initializer = None
        _init = get_post_initializers()
        if _init is not None:
            viewer_initializer, self._table_initializer = _init
            viewer_initializer.initialize_viewer(self)

        if show:
            self.show(run=False)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} widget at {hex(id(self))}>"

    @property
    def tables(self) -> TableList:
        """Return the table list object."""
        return self._tablist

    @property
    def current_table(self) -> TableBase | None:
        """Return the currently visible table."""
        if len(self.tables) > 0:
            return self.tables[self.current_index]
        return None

    @property
    def current_index(self) -> int | None:
        """Return the index of currently visible table."""
        stack = self._qwidget._tablestack
        if stack.isEmpty():
            return None
        return stack.currentIndex()

    @current_index.setter
    def current_index(self, index: int | str):
        if isinstance(index, str):
            index = self.tables.index(index)
        elif index < 0:
            index += len(self.tables)
        return self._qwidget._tablestack.setCurrentIndex(index)

    @property
    def native(self) -> _QtMainWidgetBase:
        """Return the native widget."""
        return self._qwidget

    @property
    def cell_namespace(self) -> Namespace:
        """Return the namespace of the cell editor."""
        return self._qwidget._namespace

    @property
    def history_manager(self):
        """The file I/O history manager."""
        return self._qwidget._hist_mgr

    @property
    def theme(self) -> str:
        """Get current widget theme name."""
        return self._qwidget._style_theme

    @theme.setter
    def theme(self, theme: str):
        self._qwidget.applyTheme(theme)

    def show(self, *, run: bool = True) -> None:
        """Show the widget."""
        self._qwidget.show()
        if run:
            from tabulous._qt._app import run_app

            run_app()
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

    @_doc.update_doc
    def add_table(
        self,
        data: _TableLike | None = None,
        *,
        name: str | None = None,
        editable: bool = False,
        copy: bool = True,
        metadata: dict[str, Any] | None = None,
        update: bool = False,
    ) -> Table:
        """
        Add data as a table.

        Parameters
        ----------
        data : DataFrame like, optional
            Table data to add.
        {name}{editable}{copy}{metadata}{update}

        Returns
        -------
        Table
            The added table object.
        """
        if copy:
            data = _copy_dataframe(data)
        table = Table(data, name=name, editable=editable, metadata=metadata)
        return self.add_layer(table, update=update)

    def add_spreadsheet(
        self,
        data: _TableLike | None = None,
        *,
        name: str | None = None,
        editable: bool = True,
        copy: bool = True,
        metadata: dict[str, Any] | None = None,
        update: bool = False,
        dtyped: bool = False,
    ) -> SpreadSheet:
        """
        Add data as a spreadsheet.

        Parameters
        ----------
        data : DataFrame like, optional
            Table data to add.
        {name}{editable}{copy}{metadata}{update}
        dtyped : bool, default is False
            If True, dtypes of the dataframe columns will be saved in the spreadsheet.
            Typed spreadsheet is safer for data recovery but less flexible for editing.

        Returns
        -------
        SpreadSheet
            The added spreadsheet object.
        """
        if copy:
            data = _copy_dataframe(data)
        table = SpreadSheet(data, name=name, editable=editable, metadata=metadata)
        if dtyped:
            table.dtypes.update(data.dtypes)
        return self.add_layer(table, update=update)

    def add_groupby(
        self,
        data,
        *,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        update: bool = False,
    ) -> GroupBy:
        """
        Add a groupby object.

        Parameters
        ----------
        data : DataFrameGroupBy like object
            The groupby object to add.
        {name}{metadata}{update}

        Returns
        -------
        GroupBy
            A groupby table.
        """
        table = GroupBy(data, name=name, metadata=metadata)
        return self.add_layer(table, update=update)

    def add_loader(
        self,
        loader: Callable[[], _TableLike],
        *,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        update: bool = False,
    ) -> TableDisplay:
        """
        Add a data frame loader function and continuously update the table.

        Parameters
        ----------
        loader : callable
            The loader function.
        {name}{metadata}{update}

        Returns
        -------
        TableDisplay
            A table display object.
        """
        table = TableDisplay(loader, name=name, metadata=metadata)
        return self.add_layer(table, update=update)

    def add_layer(self, input: TableBase, *, update: bool = False):
        if (
            update
            and (table := self.tables.get(input.name, None))
            and type(table) is type(input)
        ):
            table.data = input.data
            return table
        self.tables.append(input)
        self.current_index = -1  # activate the last table

        self._qwidget.setCellFocus()
        if self._table_initializer is not None:
            self._table_initializer.initialize_table(input)
        return input

    def open(self, path: PathLike, *, type: TableType | str = TableType.table) -> None:
        """
        Read a table data and add to the viewer.

        Parameters
        ----------
        path : path like
            File path.
        """
        path = Path(path)
        type = TableType(type)
        if type is TableType.table:
            fopen = self.add_table
        elif type is TableType.spreadsheet:
            fopen = self.add_spreadsheet
        else:
            raise UnreachableError(type)

        out = _io.open_file(path)
        if isinstance(out, dict):
            for sheet_name, df in out.items():
                table = fopen(df, name=sheet_name)
                table._source = Source(path)
        else:
            table = fopen(out, name=path.stem)
            table._source = Source(path)

        _utils.dump_file_open_path(path)
        return None

    def save(self, path: PathLike) -> None:
        """Save current table."""
        warnings.warn(
            "viewer.save() is deprecated. Use table.save() instead.",
            DeprecationWarning,
        )
        _io.save_file(path, self.current_table.data)
        return None

    def save_all(self, path: PathLike) -> None:
        """Save all tables."""
        path = Path(path)
        if path.is_dir():
            paths = [path / f"{table.name}.csv" for table in self.tables]
        elif path.name.count("*") == 1:
            paths = [path.replace("*", table.name) for table in self.tables]
        elif path.suffix in (".xlsx", ".xls"):
            import pandas as pd
            from tabulous._pd_index import is_ranged

            with pd.ExcelWriter(path, mode="w") as writer:
                for table in self.tables:
                    df = table.data
                    df.to_excel(
                        writer,
                        sheet_name=table.name,
                        index=not is_ranged(df.index),
                        header=not is_ranged(df.columns),
                    )
            return None
        else:
            raise ValueError("Invalid path.")

        for table, fp in zip(self.tables, paths):
            _io.save_file(fp, table.data)
        return None

    def open_sample(
        self,
        sample_name: str,
        *,
        plugin: str = "seaborn",
        type: TableType | str = TableType.table,
        asynchronous: bool = False,
    ) -> Table:
        """Open a sample table."""
        type = TableType(type)
        if type is TableType.table:
            fopen = partial(self.add_table, name=sample_name)
        elif type is TableType.spreadsheet:
            fopen = partial(self.add_spreadsheet, name=sample_name)
        else:
            raise UnreachableError(type)
        if asynchronous:
            worker = thread_worker(open_sample)(sample_name, plugin)
            worker.returned.connect(fopen)
            self.native._tablestack._info_stack.addWorker(
                worker, f"Fetching {sample_name!r} data."
            )
            worker.start()
        else:
            df = open_sample(sample_name, plugin)
            return fopen(df)

    def copy_data(
        self,
        selections: SelectionType | _SingleSelection | None = None,
        *,
        headers: bool = False,
        sep: str = "\t",
    ) -> None:
        """Copy selected cells to clipboard."""
        if selections is not None:
            self.current_table.selections = selections
        return self.current_table._qwidget.copyToClipboard(headers=headers, sep=sep)

    def paste_data(
        self,
        selections: SelectionType | _SingleSelection | None = None,
    ) -> None:
        """Paste from clipboard."""
        if selections is not None:
            self.current_table.selections = selections
        return self.current_table._qwidget.pasteFromClipBoard()

    def close(self):
        """Close the viewer."""
        return self._qwidget.close()

    @property
    def status(self) -> str:
        """Return the statup tip"""
        return self._status

    @status.setter
    def status(self, tip: str) -> None:
        """Set the status tip"""
        self._status = tip
        statusbar = self._qwidget.statusBar()
        return statusbar.showMessage(tip)

    def resize(self, width: int, height: int):
        """Resize the table viewer."""
        warnings.warn(
            "viewer.resize() is deprecated. Use `viewer.size` instead.",
            DeprecationWarning,
        )
        self.size = width, height

    @property
    def size(self) -> tuple[int, int]:
        """Return the size of the table viewer."""
        return self._qwidget.size().width(), self._qwidget.size().height()

    @size.setter
    def size(self, size: tuple[int, int]):
        """Set the size of the table viewer."""
        w, h = size
        return self._qwidget.resize(int(w), int(h))

    def _link_events(self):
        _tablist = self._tablist
        _qtablist = self._qwidget._tablestack

        @_tablist.events.inserted.connect
        def _insert_qtable(i: int):
            table = _tablist[i]
            _qtablist.addTable(table._qwidget, table.name)

        @_tablist.events.removed.connect
        def _remove_qtable(index: int, table: TableBase):
            _qtablist.blockSignals(True)
            try:
                _qtablist.takeTable(index)
            finally:
                _qtablist.blockSignals(False)

        @_tablist.events.moved.connect
        def _move_qtable(src: int, dst: int):
            # Evented list emits (0, 1) when move(0, 2) is called (v0.3.5 now).
            _qtablist.blockSignals(True)
            try:
                _qtablist.moveTable(src, dst)
            finally:
                _qtablist.blockSignals(False)

        @_tablist.events.renamed.connect
        def _rename_qtable(index: int, name: str):
            with _tablist.events.blocked():
                _qtablist.renameTable(index, name)

        @_qtablist.itemMoved.connect
        def _move_pytable(src: int, dst: int):
            """Move evented list when list is moved in GUI."""
            if src < dst:
                dst += 1
            with self._tablist.events.blocked():
                self._tablist.move(src, dst)

        @_qtablist.tableRenamed.connect
        def _rename_pytable(index: int, name: str):
            self._tablist.rename(index, name)

        @_qtablist.tableRemoved.connect
        def _remove_pytable(index: int):
            with self._tablist.events.blocked():
                del self._tablist[index]

        @_qtablist.tablePassed.connect
        def _pass_pytable(src, index: int, dst):
            src_ = _find_parent_table(src)
            dst_ = _find_parent_table(dst)
            dst_.tables.append(src_.tables.pop(index))

        _qtablist.itemDropped.connect(self.open)

        # reset choices when something changed in python table list
        _tablist.events.inserted.connect(self.reset_choices)
        _tablist.events.removed.connect(self.reset_choices)
        _tablist.events.moved.connect(self.reset_choices)
        _tablist.events.changed.connect(self.reset_choices)
        _tablist.events.renamed.connect(self.reset_choices)


class TableViewerWidget(TableViewerBase):
    """The non-main table viewer widget."""

    events: TableViewerSignal
    _qwidget: QMainWidget

    @property
    def _qwidget_class(self) -> QMainWidget:
        from tabulous._qt import QMainWidget

        return QMainWidget

    def add_widget(
        self,
        widget: Widget | QWidget,
        *,
        name: str = "",
    ):
        """Add a widget to the viewer as a child floating widget."""
        backend_widget, name = _normalize_widget(widget, name)
        backend_widget.setParent(self._qwidget, backend_widget.windowFlags())
        return backend_widget


class TableViewer(TableViewerBase):
    """The main table viewer widget."""

    events: TableViewerSignal
    _dock_widgets: weakref.WeakValueDictionary[str, QtDockWidget]
    _qwidget: QMainWindow

    @property
    def _qwidget_class(self) -> QMainWindow:
        from tabulous._qt import QMainWindow

        return QMainWindow

    def __init__(
        self,
        *,
        tab_position: TabPosition | str = TabPosition.top,
        show: bool = True,
    ):
        self._dock_widgets = weakref.WeakValueDictionary()
        self._status = ""
        super().__init__(
            tab_position=tab_position,
            show=show,
        )

    @property
    def config(self) -> MappingProxyType:
        """Return the config info."""
        from tabulous._utils import get_config

        return get_config().as_immutable()

    def add_dock_widget(
        self,
        widget: Widget | QWidget,
        *,
        name: str = "",
        area: str = "right",
        allowed_areas: list[str] | None = None,
    ):
        """
        Add a Qt or magic widget as a dock widget of the table viewer.

        Parameters
        ----------
        widget : magicgui.widgets.Widget or QWidget
            Widget to add to the table viewer.
        name : str, optional
            Name of the widget.
        area : str, default is "right"
            The initial area of the dock widget.
        allowed_areas : list of str, optional
            The allowed areas of the dock widget.
        """
        backend_widget, name = _normalize_widget(widget, name)

        dock = self._qwidget.addDockWidget(
            backend_widget, name=name, area=area, allowed_areas=allowed_areas
        )
        dock.setSourceObject(widget)
        self._dock_widgets[name] = dock
        dock.show()
        return dock

    def remove_dock_widget(self, name_or_widget: str | Widget | QWidget):
        """Remove dock widget from the table viewer."""
        if isinstance(name_or_widget, str):
            name = name_or_widget
            dock = self._dock_widgets[name_or_widget]
        else:
            for k, v in self._dock_widgets.items():
                if v is name_or_widget:
                    name = k
                    dock = v
                    break
            else:
                raise ValueError(f"Widget {name_or_widget!r} not found.")
        self._qwidget.removeDockWidget(dock)
        self._dock_widgets.pop(name)
        return None

    def reset_choices(self, *_):
        """Reset all the magicgui combo boxes."""
        for dock in self._dock_widgets.values():
            widget = dock.widget
            if hasattr(widget, "reset_choices"):
                widget.reset_choices()


class DummyViewer(_AbstractViewer):
    """
    The dummy object that emulates the table viewer.

    This is used when a table is used without a viewer, while make many commands
    still available from the table.
    """

    _namespace: Namespace | None = None

    def __init__(self, table: TableBase):
        self._table = table

    @property
    def current_table(self) -> TableBase:
        return self._table

    @property
    def current_index(self) -> int:
        return 0

    @property
    def cell_namespace(self) -> Namespace:
        """Return the namespace of the cell editor."""
        cls = self.__class__
        if cls._namespace is None:
            from tabulous._qt._mainwindow._namespace import Namespace
            from tabulous._utils import load_cell_namespace

            cls._namespace = Namespace()

            # update with user namespace
            cls._namespace.update_safely(load_cell_namespace())
        return cls._namespace


def _normalize_widget(widget: Widget | QWidget, name: str) -> tuple[QWidget, str]:
    if hasattr(widget, "native"):
        backend_widget = widget.native
        if not name:
            name = widget.name
    else:
        backend_widget = widget
        if not name:
            name = backend_widget.objectName()

    return backend_widget, name


def _copy_dataframe(data) -> pd.DataFrame:
    import pandas as pd

    if isinstance(data, pd.DataFrame):
        return data.copy()
    else:
        return Table._normalize_data(data)


def _find_parent_table(qwidget: _QtMainWidgetBase) -> TableViewerBase:
    x = qwidget
    while (parent := x.parent()) is not None:
        x = parent
        if hasattr(x, "_table_viewer"):
            return x._table_viewer
    raise RuntimeError
