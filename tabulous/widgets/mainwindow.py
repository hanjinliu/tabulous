from __future__ import annotations
from pathlib import Path
import weakref
from enum import Enum
from typing import TYPE_CHECKING, Callable, Union
from psygnal import Signal, SignalGroup

from .table import Table, SpreadSheet, GroupBy, TableDisplay
from .tablelist import TableList
from ._sample import open_sample

from ..types import SelectionType, TabPosition, _TableLike, _SingleSelection

if TYPE_CHECKING:
    from .table import TableBase
    from .._qt import QMainWindow, QMainWidget
    from .._qt._dockwidget import QtDockWidget
    from .._qt._mainwindow import _QtMainWidgetBase
    from .._qt._keymap import QtKeyMap
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


class _ComponentProxy:
    def __init__(self, parent: TableViewerBase):
        self.parent = parent

    def __repr__(self) -> str:
        return f"<{type(self).__name__} of {self.parent!r}>"


class Toolbar(_ComponentProxy):
    """The toolbar proxy."""

    @property
    def visible(self) -> bool:
        """Visibility of the toolbar."""
        return self.parent._qwidget.toolBarVisible()

    @visible.setter
    def visible(self, val) -> None:
        return self.parent._qwidget.setToolBarVisible(val)

    @property
    def history_manager(self):
        """The file I/O history manager."""
        return self.parent._qwidget._toolbar._hist_mgr

    def register_action(self, f: Callable):
        raise NotImplementedError()


class Console(_ComponentProxy):
    """The QtConsole proxy."""

    @property
    def visible(self) -> bool:
        """Visibility of the toolbar."""
        return self.parent._qwidget.consoleVisible()

    @visible.setter
    def visible(self, val) -> None:
        return self.parent._qwidget.setConsoleVisible(val)

    @property
    def buffer(self) -> str:
        """Return the current text buffer of the console."""
        return self.parent._qwidget._console_widget.input_buffer

    @buffer.setter
    def buffer(self, val) -> None:
        return self.parent._qwidget._console_widget.setBuffer(val)

    def execute(self):
        """Execute current buffer."""
        return self.parent._qwidget._console_widget.execute()


class TableViewerBase:
    events: TableViewerSignal
    _qwidget_class: type[_QtMainWidgetBase]

    def __init__(
        self, *, tab_position: TabPosition | str = TabPosition.top, show: bool = True
    ):
        from .._qt import get_app

        app = get_app()
        self._qwidget = self._qwidget_class(tab_position=tab_position)
        self._qwidget._table_viewer = self
        self._tablist = TableList(parent=self)
        self._toolbar = Toolbar(parent=self)
        self._console = Console(parent=self)
        self._link_events()

        self.events = TableViewerSignal()

        if show:
            self.show(run=False)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} widget at {hex(id(self))}>"

    def reset_choices(self, *_):
        pass

    @property
    def tables(self) -> TableList:
        """Return the table list object."""
        return self._tablist

    @property
    def toolbar(self) -> Toolbar:
        """Return the toolbar interface."""
        return self._toolbar

    @property
    def console(self) -> Console:
        """Return the console interface."""
        return self._console

    @property
    def keymap(self) -> QtKeyMap:
        """Return the keymap object."""
        return self._qwidget._keymap

    @property
    def current_table(self) -> TableBase | None:
        """Return the currently visible table."""
        if len(self.tables) > 0:
            return self.tables[self.current_index]
        return None

    @property
    def current_index(self) -> int:
        """Return the index of currently visible table."""
        return self._qwidget._tablestack.currentIndex()

    @property
    def native(self) -> _QtMainWidgetBase:
        """Return the native widget."""
        return self._qwidget

    @current_index.setter
    def current_index(self, index: int | str):
        if isinstance(index, str):
            index = self.tables.index(index)
        elif index < 0:
            index += len(self.tables)
        return self._qwidget._tablestack.setCurrentIndex(index)

    def show(self, *, run: bool = True) -> None:
        """Show the widget."""
        self._qwidget.show()
        if run:
            from .._qt._app import run_app

            run_app()
        return None

    def screenshot(self) -> np.ndarray:
        """Get screenshot of the widget."""
        return self._qwidget.screenshot()

    def add_table(
        self,
        data: _TableLike | None = None,
        *,
        name: str | None = None,
        editable: bool = False,
        copy: bool = True,
        update: bool = False,
    ) -> TableBase:

        """
        Add data as a table.

        Parameters
        ----------
        data : DataFrame like, optional
            Table data to add.
        name : str, optional
            Name of the table.
        editable : bool, default is False
            Whether the table is editable via UI.
        copy : bool, default is True
            Whether to copy the data before adding to avoid overwriting the original one.
        update : bool, default is False
            If True, update the table data if a table of same name exists.

        Returns
        -------
        TableLayerBase
            The added table object.
        """
        if copy:
            data = _copy_dataframe(data)
        table = Table(data, name=name, editable=editable)
        return self.add_layer(table, update=update)

    def add_spreadsheet(
        self,
        data: _TableLike | None = None,
        *,
        name: str | None = None,
        editable: bool = True,
        copy: bool = True,
        update: bool = False,
    ) -> SpreadSheet:
        """
        Add data as a spreadsheet.

        Parameters
        ----------
        data : DataFrame like, optional
            Table data to add.
        name : str, optional
            Name of the table.
        editable : bool, default is False
            Whether the table is editable via UI.
        copy : bool, default is True
            Whether to copy the data before adding to avoid overwriting the original one.

        Returns
        -------
        SpreadSheet
            The added spreadsheet object.
        """
        if copy:
            data = _copy_dataframe(data)
        table = SpreadSheet(data, name=name, editable=editable)
        return self.add_layer(table, update=update)

    def add_groupby(
        self, data, name: str | None = None, update: bool = False
    ) -> GroupBy:
        """Add a groupby."""
        table = GroupBy(data, name=name)
        return self.add_layer(table, update=update)

    def add_loader(self, loader, name: str | None = None) -> TableDisplay:
        """Add a table loader."""
        table = TableDisplay(loader, name=name)
        return self.add_layer(table)

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
        suf = path.suffix
        type = TableType(type)
        if type == TableType.table:
            fopen = self.add_table
        elif type == TableType.spreadsheet:
            fopen = self.add_spreadsheet
        else:
            raise RuntimeError

        import pandas as pd

        if suf in (".csv", ".txt", ".dat"):
            df = pd.read_csv(path)
            fopen(df, name=path.stem)
        elif suf in (".xlsx", ".xls", ".xlsb", ".xlsm", ".xltm", "xltx", ".xml"):
            df_dict: dict[str, pd.DataFrame] = pd.read_excel(path, sheet_name=None)
            for sheet_name, df in df_dict.items():
                fopen(df, name=sheet_name)
        elif suf in (".parquet",):
            df = pd.read_parquet(path)
            fopen(df)
        else:
            raise ValueError(f"Extension {suf} not supported.")

    def save(self, path: PathLike) -> None:
        """Save current table."""
        path = Path(path)
        suf = path.suffix
        df = self.current_table.data
        if suf in (".csv", ".txt", ".dat"):
            df.to_csv(path)
        elif suf in (".xlsx", ".xls", "xml"):
            df.to_excel(path)
        elif suf in (".html",):
            df.to_html(path)
        elif suf in (".parquet",):
            df.to_parquet(path)
        else:
            raise ValueError(f"Extension {suf} not supported.")

    def open_sample(self, sample_name: str, plugin: str = "seaborn") -> Table:
        """Open a sample table."""
        df = open_sample(sample_name, plugin)
        return self.add_table(df, name=sample_name)

    def copy_data(
        self,
        selections: SelectionType | _SingleSelection | None = None,
        *,
        headers: bool = False,
    ) -> None:
        """Copy selected cells to clipboard."""
        if selections is not None:
            self.current_table.selections = selections
        return self.current_table._qwidget.copyToClipboard(headers=headers)

    def paste_data(
        self,
        selections: SelectionType | _SingleSelection | None = None,
    ) -> None:
        """Paste from clipboard."""
        if selections is not None:
            self.current_table.selections = selections
        return self.current_table._qwidget.pasteFromClipBoard()

    def _link_events(self):
        _tablist = self._tablist
        _qtablist = self._qwidget._tablestack

        @_tablist.events.inserted.connect
        def _insert_qtable(i: int):
            table = _tablist[i]
            _qtablist.addTable(table._qwidget, table.name)

        @_tablist.events.removed.connect
        def _remove_qtable(index: int, table: TableBase):
            with _tablist.events.blocked():
                _qtablist.takeTable(index)

        @_tablist.events.moved.connect
        def _move_qtable(src: int, dst: int):
            # Evented list emits (0, 1) when move(0, 2) is called (v0.3.5 now).
            if src < dst:
                dst += 1
            with _tablist.events.blocked():
                _qtablist.moveTable(src, dst)

        @_tablist.events.renamed.connect
        def _rename_qtable(index: int, name: str):
            with _tablist.events.blocked():
                _qtablist.renameTable(index, name)

        @_qtablist.itemMoved.connect
        def _move_pytable(src: int, dst: int):
            """Move evented list when list is moved in GUI."""
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
        from .._qt import QMainWidget

        return QMainWidget

    def add_widget(
        self,
        widget: Widget | QWidget,
        *,
        name: str = "",
    ):
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
        from .._qt import QMainWindow

        return QMainWindow

    def __init__(
        self,
        *,
        tab_position: TabPosition | str = TabPosition.top,
        show: bool = True,
    ):
        self._dock_widgets = weakref.WeakValueDictionary()
        super().__init__(
            tab_position=tab_position,
            show=show,
        )

    # def register_action(self, location: str):
    #     return self._qwidget.registerAction(location)

    @property
    def status(self) -> str:
        """Return the statup tip"""
        return self._qwidget.statusTip()

    @status.setter
    def status(self, tip: str) -> None:
        """Set the status tip"""
        return self._qwidget.setStatusTip(tip)

    def add_dock_widget(
        self,
        widget: Widget | QWidget,
        *,
        name: str = "",
        area: str = "right",
        allowed_areas: list[str] | None = None,
    ):
        backend_widget, name = _normalize_widget(widget, name)

        dock = self._qwidget.addDockWidget(
            backend_widget, name=name, area=area, allowed_areas=allowed_areas
        )
        dock.setSourceObject(widget)
        self._dock_widgets[name] = dock
        return dock

    def remove_dock_widget(self, name_or_widget: str | Widget | QWidget):
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
        for dock in self._dock_widgets.values():
            widget = dock.widget
            if hasattr(widget, "reset_choices"):
                widget.reset_choices()


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

    return pd.DataFrame(data, copy=True)


def _find_parent_table(qwidget: _QtMainWidgetBase) -> TableViewerBase:
    x = qwidget
    while (parent := x.parent()) is not None:
        x = parent
        if hasattr(x, "_table_viewer"):
            return x._table_viewer
    raise RuntimeError
