from __future__ import annotations
from typing import Any, Callable, Iterable, TYPE_CHECKING, TypeVar, cast
import warnings
import datetime
import inspect

from qtpy import QtWidgets as QtW, QtGui
from magicgui import register_type, magicgui
from magicgui.widgets import (
    Widget,
    Container,
    ComboBox,
    Label,
    Dialog,
    PushButton,
    LineEdit,
)
from magicgui.backends._qtpy.widgets import QBaseWidget

from tabulous.widgets import (
    TableViewerBase,
    TableBase,
    Table,
    SpreadSheet,
    TableViewerWidget,
    MagicTable,
)
from tabulous.types import (
    TableColumn,
    TableData,
    TableDataTuple,
    TableInfoInstance,
    TabPosition,
)
from tabulous._selection_op import (
    SelectionOperator,
    ILocSelOp,
    parse,
    construct,
)

from tabulous._timedelta import TimeDeltaEdit

if TYPE_CHECKING:
    import pandas as pd
    from magicgui.widgets import FunctionGui
    from matplotlib.axes import Axes
else:
    Axes = Any


# #############################################################################
#    magicgui-widget
# #############################################################################


class MagicTableViewer(Widget, TableViewerWidget):
    """
    A magicgui widget of table viewer.

    This class is a subclass of ``magicgui.widget.Widget`` so that it can be used
    in a compatible way with magicgui and napari.

    Parameters
    ----------
    tab_position: TabPosition or str
        Type of list-like widget to use.
    """

    def __init__(
        self,
        *,
        tab_position: TabPosition | str = TabPosition.top,
        name: str = "",
        label: str = None,
        tooltip: str | None = None,
        visible: bool | None = None,
        enabled: bool = True,
        show: bool = False,
    ):
        super().__init__(
            widget_type=QBaseWidget,
            backend_kwargs={"qwidg": QtW.QWidget},
            name=name,
            label=label,
            tooltip=tooltip,
            visible=visible,
            enabled=enabled,
        )
        TableViewerWidget.__init__(self, tab_position=tab_position, show=False)
        mgui_native: QtW.QWidget = self._widget._mgui_get_native_widget()
        mgui_native.setLayout(QtW.QVBoxLayout())
        mgui_native.layout().addWidget(self._qwidget)
        mgui_native.setContentsMargins(0, 0, 0, 0)
        if show:
            self.show(run=False)

    @property
    def native(self):
        try:
            return TableViewerWidget.native.fget(self)
        except AttributeError:
            return Widget.native.fget(self)


# #############################################################################
#    magicgui type registration
# #############################################################################

_DEFAULT_NAME = "Result"


def find_table_viewer_ancestor(widget: Widget | QtW.QWidget) -> TableViewerBase | None:
    from tabulous._qt._mainwindow import _QtMainWidgetBase

    if isinstance(widget, Widget):
        qwidget = widget.native
    elif isinstance(widget, QtW.QWidget):
        qwidget = widget
    else:
        raise TypeError(f"Cannot use {type(widget)} as an input.")
    qwidget: QtW.QWidget
    while True:
        if isinstance(qwidget, _QtMainWidgetBase):
            qwidget = cast(_QtMainWidgetBase, qwidget)
            return qwidget._table_viewer
        qwidget = qwidget.parent()
        if qwidget is None:
            return None


def find_current_table(widget: Widget | QtW.QWidget) -> TableBase | None:
    viewer = find_table_viewer_ancestor(widget)
    if viewer is None:
        return None
    table = viewer.current_table
    if table is None:
        return None
    return table


def get_any_tables(widget: Widget) -> list[tuple[str, Any]]:
    """Get the list of available tables and the names."""
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return [(t.name, t) for t in v.tables]


def get_tables(widget: Widget) -> list[tuple[str, Any]]:
    """Get the list of available tables and the names."""
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return [(t.name, t) for t in v.tables if isinstance(t, Table)]


def get_spreasheets(widget: Widget) -> list[tuple[str, Any]]:
    """Get the list of available table data and the names."""
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return [(t.name, t) for t in v.tables if isinstance(t, SpreadSheet)]


def get_table_data(widget: Widget) -> list[tuple[str, Any]]:
    """Get the list of available table data and the names."""
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return [(table.name, table.data) for table in v.tables]


def open_viewer(gui, result: TableViewerBase, return_type: type):
    return result.show()


def add_table_to_viewer(
    gui: FunctionGui,
    result: Any,
    return_type: type,
) -> None:
    viewer = find_table_viewer_ancestor(gui)
    if viewer is None:
        return
    viewer.add_layer(result, update=True)


def add_table_data_to_viewer(gui: FunctionGui, result: Any, return_type: type) -> None:
    viewer = find_table_viewer_ancestor(gui)
    if viewer is None:
        return

    from pandas.core.groupby.generic import DataFrameGroupBy

    if isinstance(result, DataFrameGroupBy):
        viewer.add_groupby(result, name=f"{gui.name}-{_DEFAULT_NAME}", update=True)
    else:
        viewer.add_table(result, name=f"{gui.name}-{_DEFAULT_NAME}", update=True)


def add_table_data_tuple_to_viewer(
    gui: FunctionGui,
    result: tuple,
    return_type: type,
):
    viewer = find_table_viewer_ancestor(gui)
    if viewer is None:
        return
    n = len(result)
    if n == 1:
        data = (result[0], f"{gui.name}-{_DEFAULT_NAME}", {})
    elif n == 2:
        if isinstance(result[1], dict):
            name = result[1].pop("name", f"{gui.name}-{_DEFAULT_NAME}")
            data = (result[0], name, result[1])
        else:
            data = (result[0], result[1], {})
    elif n == 3:
        data = result
    else:
        raise ValueError(f"Length of TableDataTuple must be < 4, got {n}.")
    viewer.add_table(data[0], name=data[1], **data[2], update=True)


register_type(
    TableViewerBase,
    return_callback=open_viewer,
    bind=find_table_viewer_ancestor,
)
register_type(TableBase, return_callback=add_table_to_viewer, choices=get_any_tables)
register_type(Table, return_callback=add_table_to_viewer, choices=get_tables)
register_type(SpreadSheet, return_callback=add_table_to_viewer, choices=get_spreasheets)
register_type(
    TableData,
    return_callback=add_table_data_to_viewer,
    choices=get_table_data,
    nullable=False,
)
register_type(TableDataTuple, return_callback=add_table_data_tuple_to_viewer)

# Widget
class ColumnChoice(Container):
    def __init__(
        self,
        data_choices: Iterable[pd.DataFrame]
        | Callable[[Widget], Iterable[pd.DataFrame]],
        value=None,
        **kwargs,
    ):
        self._dataframe_choices = ComboBox(choices=data_choices, value=value, **kwargs)
        self._column_choices = ComboBox(choices=self._get_available_columns)
        _label_l = Label(value='["')
        _label_l.max_width = 24
        _label_r = Label(value='"]')
        _label_r.max_width = 24
        super().__init__(
            layout="horizontal",
            widgets=[self._dataframe_choices, _label_l, self._column_choices, _label_r],
            labels=False,
            name=kwargs.get("name"),
        )
        self.margins = (0, 0, 0, 0)
        self._dataframe_choices.changed.connect(self._set_available_columns)

    def _get_available_columns(self, w=None):
        df: pd.DataFrame = self._dataframe_choices.value
        cols = getattr(df, "columns", [])
        return cols

    def _set_available_columns(self, w=None):
        cols = self._get_available_columns()
        self._column_choices.choices = cols
        return None

    @property
    def value(self) -> pd.Series:
        df = self._dataframe_choices.value
        return df[self._column_choices.value]


register_type(
    TableColumn,
    widget_type=ColumnChoice,
    return_callback=add_table_data_to_viewer,
    data_choices=get_table_data,
    nullable=False,
)


class ColumnNameChoice(Container):
    """
    A container widget with a DataFrame selection and multiple column name selections.

    This widget is composed of two or more ComboBox widgets. The top one is to choose a
    DataFrame and the rest are to choose column names from the DataFrame. When the
    DataFrame selection changed, the column name selections will also changed
    accordingly.
    """

    def __init__(
        self,
        data_choices: Iterable[pd.DataFrame]
        | Callable[[Widget], Iterable[pd.DataFrame]],
        column_choice_names: Iterable[str],
        value=None,
        **kwargs,
    ):
        self._dataframe_choices = ComboBox(choices=data_choices, value=value, **kwargs)
        self._column_names: list[ComboBox] = []
        for cn in column_choice_names:
            self._column_names.append(
                ComboBox(choices=self._get_available_columns, name=cn, nullable=True)
            )
        self._child_container = Container(widgets=self._column_names, layout="vertical")
        self._child_container.margins = (0, 0, 0, 0)
        super().__init__(
            layout="vertical",
            widgets=[self._dataframe_choices, self._child_container],
            labels=False,
            name=kwargs.get("name"),
        )
        self.margins = (0, 0, 0, 0)
        self._dataframe_choices.changed.connect(self._set_available_columns)

    def _get_available_columns(self, w=None):
        df: pd.DataFrame = self._dataframe_choices.value
        cols = getattr(df, "columns", [])
        return cols

    def _set_available_columns(self, w=None):
        cols = self._get_available_columns()
        for cbox in self._column_names:
            cbox.choices = cols
        return None

    @property
    def value(self) -> tuple[pd.DataFrame, list[str]]:
        df = self._dataframe_choices.value
        colnames = [cbox.value for cbox in self._column_names]
        return (df, colnames)


register_type(
    TableInfoInstance, widget_type=ColumnNameChoice, data_choices=get_table_data
)

# #############################################################################
#    Utility functions
# #############################################################################

_F = TypeVar("_F", bound=Callable)


def dialog_factory(function: _F) -> _F:
    from magicgui.widgets import create_widget

    def _runner(parent=None, **param_options):
        # create a list of widgets, similar to magic_signature
        widgets: list[Widget] = []
        callbacks: dict[str, Callable[[Widget], Any]] = {}
        sig = inspect.signature(function)
        for name, param in sig.parameters.items():
            opt = param_options.get(name, {})
            opt.setdefault("gui_only", False)
            changed_cb = opt.pop("changed", None)
            if param.default is not inspect.Parameter.empty:
                opt.setdefault("value", param.default)
            if param.annotation is not inspect.Parameter.empty:
                opt.setdefault("annotation", param.annotation)
            opt.setdefault("name", name)
            kwargs: dict[str, Any] = {}
            for k in "value", "annotation", "name", "label", "widget_type", "gui_only":
                if k in opt:
                    kwargs[k] = opt.pop(k)
            widget = create_widget(**kwargs, options=opt)
            if changed_cb is not None:
                assert callable(changed_cb)
                callbacks[name] = changed_cb
            widgets.append(widget)

        dlg = Dialog(widgets=widgets)

        for name, cb in callbacks.items():
            dlg[name].changed.connect(lambda: cb(dlg))

        # if return annotation "TableData" is given, add a preview widget.
        if function.__annotations__.get("return") is TableData:
            table = MagicTable(
                data=[],
                name="preview",
                editable=False,
                tooltip="Preview of the result using the head of the input data.",
                gui_only=True,
            )
            table.zoom = 0.8
            dlg.append(table)

            @dlg.changed.connect
            def _on_value_change(*_):
                import pandas as pd

                kwargs = dlg.asdict()
                # Check the first data frame is not too large.
                argname, val = next(iter(kwargs.items()))
                if isinstance(val, pd.DataFrame):
                    num = 8400
                    if val.size > num:
                        kwargs[argname] = val.head(num // val.shape[1])
                try:
                    table.data = function(**kwargs)
                except Exception:
                    table.data = []

            dlg.changed.emit()

        dlg.native.setParent(parent, dlg.native.windowFlags())
        dlg._shortcut = QtW.QShortcut(QtGui.QKeySequence("Ctrl+W"), dlg.native)
        dlg._shortcut.activated.connect(dlg.close)
        dlg.reset_choices()
        if dlg.exec():
            out = function(**dlg.asdict())
        else:
            out = None
        return out

    return _runner


def dialog_factory_mpl(function: _F) -> _F:
    def _runner(parent=None, **param_options):
        dlg = magicgui(function, **param_options)

        from tabulous._qt._plot import QtMplPlotCanvas

        style = None
        bg = None
        if parent is not None:
            if viewer := find_table_viewer_ancestor(parent):
                if not viewer._qwidget._white_background:
                    style = "dark_background"
                bg = viewer._qwidget.backgroundColor().name()

        plt = QtMplPlotCanvas(style=style)
        if bg:
            plt.set_background_color(bg)

        dlg.native.layout().addWidget(plt)
        dlg.height = 400
        dlg.width = 280

        @dlg.changed.connect
        def _on_value_change(*_):
            kwargs = dlg.asdict()
            kwargs["ax"] = plt.ax
            if kwargs.get("ref", False):
                kwargs["ref"] = False
            try:
                plt.cla()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    function(**kwargs)
                plt.draw()
            except Exception:
                pass

        dlg.changed.emit()

        dlg.native.setParent(parent, dlg.native.windowFlags())
        dlg._shortcut = QtW.QShortcut(QtGui.QKeySequence("Ctrl+W"), dlg.native)
        dlg._shortcut.activated.connect(dlg.close)
        dlg.called.connect(lambda: dlg.close())
        return dlg.show()

    return _runner


# #############################################################################
#   Selection widget
# #############################################################################


class SelectionWidget(Container):
    """A container widget for a table selection."""

    def __init__(
        self,
        value: Any = None,
        nullable=False,
        format: str = "iloc",
        allow_out_of_bounds: bool = False,
        **kwargs,
    ):
        self._line = LineEdit(tooltip="Selection string (e.g. 'df.iloc[2:4, 3:]')")
        self._btn = PushButton(
            text="Read selection", tooltip="Read current table selection."
        )
        super().__init__(layout="horizontal", widgets=[self._line, self._btn], **kwargs)
        self.margins = (0, 0, 0, 0)
        self._line.changed.disconnect()
        self._btn.changed.disconnect()
        self._line.changed.connect(self.changed.emit(self._line.value))
        self._btn.changed.connect(lambda: self._read_selection())

        self._format = format
        self._allow_out_of_bounds = allow_out_of_bounds

        if isinstance(value, (str, SelectionOperator, tuple)):
            self.value = value

    @property
    def value(self) -> SelectionOperator | None:
        """Get selection operator that represents current selection."""
        text = self._line.value
        if text:
            return parse(text, df_expr="df")
        return None

    @value.setter
    def value(self, val: str | SelectionOperator) -> None:
        if isinstance(val, str):
            if val:
                text = parse(val, df_expr="df").fmt()
            else:
                text = ""
        elif isinstance(val, SelectionOperator):
            text = val.fmt()
        elif isinstance(val, tuple):
            text = ILocSelOp(*val).fmt()
        elif val is None:
            text = ""
        else:
            raise TypeError(f"Invalid type for value: {type(val)}")
        self._line.value = text
        return None

    @property
    def format(self) -> str:
        return self._format

    def as_iloc(self) -> tuple[slice, slice]:
        """Return current value as a indexer for ``iloc`` method."""
        df = self._find_table().data_shown
        return self.value.as_iloc(df)

    def as_iloc_slices(self) -> tuple[slice, slice]:
        """Return current value as slices for ``iloc`` method."""
        df = self._find_table().data_shown
        return self.value.as_iloc_slices(df)

    def _find_table(self) -> TableBase:
        table = find_current_table(self)
        if table is None:
            raise ValueError("No table found.")
        return table

    def _read_selection(self, table: TableBase | None = None):
        if table is None:
            table = self._find_table()

        sels = table.selections
        if len(sels) > 1:
            raise ValueError("More than one selection is given.")
        sel = sels[0]

        qwidget = table.native
        column_selected = qwidget._qtable_view._selection_model._col_selection_indices
        if isinstance(table, SpreadSheet):
            df = table.native._data_raw
        else:
            df = table.data_shown
        _selop = construct(
            *sel,
            df,
            method=self.format,
            column_selected=column_selected,
            allow_out_of_bounds=self._allow_out_of_bounds,
        )
        self._line.value = _selop.fmt()
        self.changed.emit(_selop)
        return None


register_type(SelectionOperator, widget_type=SelectionWidget)

register_type(datetime.timedelta, widget_type=TimeDeltaEdit)
