from __future__ import annotations
from typing import Any, Callable, Iterable, TYPE_CHECKING, TypeVar
import warnings
from qtpy.QtWidgets import QWidget, QVBoxLayout
from magicgui import register_type
from magicgui.widgets import Widget, Container, ComboBox, Label, Dialog
from magicgui.widgets._bases import CategoricalWidget
from magicgui.backends._qtpy.widgets import QBaseWidget

from .widgets import TableViewer, Table, SpreadSheet, TableViewerWidget
from .types import (
    TableColumn,
    TableData,
    TableDataTuple,
    TableInfoInstance,
    TabPosition,
)

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
    ):
        super().__init__(
            widget_type=QBaseWidget,
            backend_kwargs={"qwidg": QWidget},
            name=name,
            label=label,
            tooltip=tooltip,
            visible=visible,
            enabled=enabled,
        )
        TableViewerWidget.__init__(self, tab_position=tab_position, show=False)
        self.native: QWidget
        self.native.setLayout(QVBoxLayout())
        self.native.layout().addWidget(self._qwidget)
        self.native.setContentsMargins(0, 0, 0, 0)


class MagicTable(Widget, Table):
    def __init__(
        self,
        data: Any | None = None,
        *,
        name: str = "",
        editable: bool = False,
        label: str = None,
        tooltip: str | None = None,
        visible: bool | None = None,
        enabled: bool = True,
        gui_only: bool = False,
    ):
        Table.__init__(self, data, name=name, editable=editable)
        super().__init__(
            widget_type=QBaseWidget,
            backend_kwargs={"qwidg": QWidget},
            name=name,
            label=label,
            tooltip=tooltip,
            visible=visible,
            enabled=enabled,
            gui_only=gui_only,
        )
        self.native: QWidget
        self.native.setLayout(QVBoxLayout())
        self.native.layout().addWidget(self._qwidget)
        self.native.setContentsMargins(0, 0, 0, 0)


# #############################################################################
#    magicgui type registration
# #############################################################################

_DEFAULT_NAME = "Result"


def find_table_viewer_ancestor(widget: Widget | QWidget) -> TableViewer | None:
    from ._qt._mainwindow import _QtMainWidgetBase

    if isinstance(widget, Widget):
        qwidget = widget.native
    elif isinstance(widget, QWidget):
        qwidget = widget
    else:
        raise TypeError(f"Cannot use {type(widget)} as an input.")
    qwidget: QWidget
    parent = qwidget.parent()
    while (parent := qwidget.parent()) is not None:
        qwidget = parent
        if isinstance(qwidget, _QtMainWidgetBase):
            return qwidget._table_viewer

    return None


def get_tables(widget: CategoricalWidget) -> list[tuple[str, Any]]:
    """Get the list of available tables and the names."""
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return v.tables


def get_table_data(widget: CategoricalWidget) -> list[tuple[str, Any]]:
    """Get the list of available table data and the names."""
    v = find_table_viewer_ancestor(widget)
    if v is None:
        return []
    return [(table.name, table.data) for table in v.tables]


def open_viewer(gui, result: TableViewer, return_type: type):
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
    TableViewer, return_callback=open_viewer, choices=find_table_viewer_ancestor
)
register_type(Table, return_callback=add_table_to_viewer, choices=get_tables)
register_type(SpreadSheet, return_callback=add_table_to_viewer, choices=get_tables)
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
    DataFrame and the rest are to choose column names from the DataFrame. When the DataFrame
    selection changed, the column name selections will also changed accordingly.
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
    from magicgui.signature import magic_signature

    def _runner(parent=None, **param_options):
        widgets = list(
            magic_signature(function, gui_options=param_options).widgets().values()
        )
        dlg = Dialog(widgets=widgets)

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
        if dlg.exec():
            out = function(**dlg.asdict())
        else:
            out = None
        return out

    return _runner


def dialog_factory_mpl(function: _F) -> _F:

    from magicgui.signature import magic_signature

    def _runner(parent=None, **param_options):
        widgets = list(
            magic_signature(function, gui_options=param_options).widgets().values()
        )
        dlg = Dialog(widgets=widgets)

        from ._qt._plot import QtMplPlotCanvas

        plt = QtMplPlotCanvas()
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
        if dlg.exec():
            out = function(**dlg.asdict())
        else:
            out = None
        return out

    return _runner
