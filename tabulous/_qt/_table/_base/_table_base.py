from __future__ import annotations
from functools import partial
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING, Tuple, TypeVar
import warnings
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Signal, Qt

import numpy as np
import pandas as pd
from collections_undo import fmt

from ._item_model import AbstractDataFrameModel
from ._line_edit import QHorizontalHeaderLineEdit, QVerticalHeaderLineEdit
from .._dtype import isna
from ..._undo import QtUndoManager, fmt_slice
from ..._svg import QColoredSVGIcon
from ..._keymap import QtKeys, QtKeyMap
from ..._action_registry import QActionRegistry
from ....types import FilterType, ItemInfo, HeaderInfo, EvalInfo
from ....exceptions import SelectionRangeError, TableImmutableError

if TYPE_CHECKING:
    from ._delegate import TableItemDelegate
    from ._side_area import QTableSideArea
    from ._enhanced_table import _QTableViewEnhanced
    from ..._table_stack import QTabbedTableStack
    from ..._mainwindow import _QtMainWidgetBase
    from ....types import SelectionType, _Sliceable
    from ...._eval import Graph

ICON_DIR = Path(__file__).parent.parent.parent / "_icons"

_SplitterStyle = """
QSplitter::handle:horizontal {
    background-color: gray;
    border: 0px;
    width: 4px;
    margin-top: 5px;
    margin-bottom: 5px;
    border-radius: 2px;}
"""


class QTableHandle(QtW.QSplitterHandle):
    """The handle widget used to resize the side area."""

    def __init__(self, o: Qt.Orientation, parent: QtW.QSplitter) -> None:
        super().__init__(o, parent)
        self._sizes = parent.sizes()

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent) -> None:
        """Collapse/expand side area."""
        parent = self.splitter()
        sizes = parent.sizes()
        if sizes[1] == 0:
            parent.setSizes(self._sizes)
        else:
            self._sizes = sizes
            parent.setSizes([1, 0])

        return super().mouseDoubleClickEvent(a0)


class QBaseTable(QtW.QSplitter, QActionRegistry[Tuple[int, int]]):
    """
    The base widget for a table.

    Abstract Methods
    ----------------
    def createQTableView(self) -> None: ...
    def getDataFrame(self) -> pd.DataFrame: ...
    def setDataFrame(self) -> None: ...
    def createModel(self) -> AbstractDataFrameModel: ...
    def tableSlice(self) -> pd.DataFrame: ...
    """

    selectionChangedSignal = Signal()
    _DEFAULT_EDITABLE = False
    _mgr = QtUndoManager()
    _keymap = QtKeyMap()

    def __init__(
        self, parent: QtW.QWidget | None = None, data: pd.DataFrame | None = None
    ):
        QtW.QSplitter.__init__(self, parent)
        QActionRegistry.__init__(self)

        self._filter_slice: FilterType | None = None
        self._filtered_index: pd.Index | None = None
        self._filtered_columns: pd.Index | None = None
        self.setContentsMargins(0, 0, 0, 0)

        self.createQTableView()
        self.createModel()
        self.setDataFrame(data)

        self._qtable_view.selectionChangedSignal.connect(
            self.selectionChangedSignal.emit
        )

        self._side_area: QTableSideArea = None
        self.model()._editable = self._DEFAULT_EDITABLE
        self.setStyleSheet(_SplitterStyle)

        self._qtable_view.rightClickedSignal.connect(self.showContextMenu)
        self._install_actions()

        self.selectionChangedSignal.connect(self._try_update_console)

    def createHandle(self) -> QTableHandle:
        """Create custom handle."""
        return QTableHandle(Qt.Orientation.Horizontal, self)

    def showContextMenu(self, pos: QtCore.QPoint):
        index = self._qtable_view.indexAt(pos)
        if not index.isValid():
            return None

        row, col = index.row(), index.column()
        sel_model = self._qtable_view._selection_model
        highlight_model = self._qtable_view._highlight_model

        if sel_model._ctrl_on:
            # if Ctrl is on, select the highlight under the cursor.
            idx, rng = highlight_model.range_under_index(row, col)
            if rng is not None:
                if len(highlight_model._selected_indices) == 0:
                    self.setSelections([rng])
                else:
                    self.setSelections(self.selections() + [rng])
                highlight_model.add_selection(idx)
            else:
                self.setSelections([(row, col)])
                highlight_model.select([])
        else:
            idx, rng = sel_model.range_under_index(row, col)
            if rng is not None:
                sel_model.reorder_to_last(idx)
                self.update()
            else:
                self.setSelections([(row, col)])
            highlight_model.select([])

        return self.execContextMenu((row, col))

    def _install_actions(self):
        # fmt: off
        hheader = self._qtable_view.horizontalHeader()
        hheader.registerAction("Color>Set foreground colormap")(self._set_forground_colormap_with_dialog)
        hheader.registerAction("Color>Reset foreground colormap")(self._reset_forground_colormap)
        hheader.registerAction("Color>Set background colormap")(self._set_background_colormap_with_dialog)
        hheader.registerAction("Color>Reset background colormap")(self._reset_background_colormap)
        hheader.registerAction("Formatter>Set text formatter")(self._set_text_formatter_with_dialog)
        hheader.registerAction("Formatter>Reset text formatter")(self._reset_text_formatter)
        hheader.addSeparator()

        self.registerAction("Copy")(lambda index: self.copyToClipboard(headers=False))
        self.registerAction("Copy as ...>Tab separated text")(lambda index: self.copyToClipboard(headers=False, sep="\t"))
        self.registerAction("Copy as ...>Tab separated text with headers")(lambda index: self.copyToClipboard(headers=True, sep="\t"))
        self.registerAction("Copy as ...>Comma separated text")(lambda index: self.copyToClipboard(headers=False, sep=","))
        self.registerAction("Copy as ...>Comma separated text with headers")(lambda index: self.copyToClipboard(headers=True, sep=","))
        self.registerAction("Copy as ...>Literal")(lambda index: self._copy_as_literal())
        self.registerAction("Paste")(lambda index: self.pasteFromClipBoard())
        self.registerAction("Paste from ...>Comma separated text")(lambda index: self.pasteFromClipBoard(sep=","))
        self.addSeparator()
        self.registerAction("Add highlight")(lambda index: self.setHighlights(self.highlights() + self.selections()))
        self.registerAction("Delete highlight")(lambda index: self._delete_selected_highlights())
        self.addSeparator()
        # fmt: on
        return None

    # fmt: off
    if TYPE_CHECKING:
        def handle(self, pos: int) -> QTableHandle: ...
    # fmt: on

    @property
    def _qtable_view(self) -> _QTableViewEnhanced:
        raise NotImplementedError()

    @property
    def _central_widget(self) -> QtW.QWidget:
        return self._qtable_view

    def createQTableView(self) -> None:
        """Create QTableView."""
        raise NotImplementedError()

    def getDataFrame(self) -> pd.DataFrame:
        raise NotImplementedError()

    def setDataFrame(self, df: pd.DataFrame) -> None:
        raise NotImplementedError()

    def createModel(self) -> AbstractDataFrameModel:
        raise NotImplementedError()

    def tableSlice(self) -> pd.DataFrame:
        raise NotImplementedError()

    def tableShape(self) -> tuple[int, int]:
        model = self._qtable_view.model()
        nr = model.rowCount()
        nc = model.columnCount()
        return (nr, nc)

    def dataShape(self) -> tuple[int, int]:
        return self.tableShape()

    def zoom(self) -> float:
        """Get current zoom factor."""
        return self._qtable_view.zoom()

    def setZoom(self, value: float) -> None:
        """Set zoom factor."""
        return self._qtable_view.setZoom(value)

    def itemDelegate(self) -> TableItemDelegate:
        return QtW.QTableView.itemDelegate(self._qtable_view)

    def model(self) -> AbstractDataFrameModel:
        return self._qtable_view.model()

    def setDataFrameValue(self, row: int, col: int, value: Any) -> None:
        raise TableImmutableError("Table is immutable.")

    def deleteValues(self) -> None:
        raise TableImmutableError("Table is immutable.")

    def setVerticalHeaderValue(self, index: int, value: Any) -> None:
        raise TableImmutableError("Table is immutable.")

    def setHorizontalHeaderValue(self, index: int, value: Any) -> None:
        raise TableImmutableError("Table is immutable.")

    def isEditable(self) -> bool:
        """Return the editability of the table."""
        return False

    def setEditable(self, editable: bool):
        """Set the editability of the table."""
        if editable:
            raise TableImmutableError("Table is immutable.")

    def assignColumn(self, ds: pd.Series):
        raise TableImmutableError("Table is immutable.")

    def convertValue(self, r: int, c: int, value: Any) -> Any:
        """Convert value before updating DataFrame."""
        return value

    def _get_converter(self, c: int) -> Callable[[Any], Any]:
        if 0 <= c < len(self._filtered_columns):
            colname = self._filtered_columns[c]
            if validator := self.model()._validator.get(colname, None):
                return partial(
                    _convert_value, validator=validator, converter=self.convertValue
                )
        return self.convertValue

    def dataShown(self, parse: bool = False) -> pd.DataFrame:
        """Return the shown dataframe (consider filter)."""
        return self.model().df

    def connectSelectionChangedSignal(self, slot):
        self.selectionChangedSignal.connect(slot)
        return slot

    def selections(self) -> SelectionType:
        """Get list of selections as slicable tuples"""
        return self._qtable_view._selection_model._ranges

    def setSelections(self, selections: SelectionType):
        """Set list of selections."""
        qtable = self._qtable_view
        qtable.clear_selections()
        nr, nc = self.tableShape()
        qtable.set_selections(_normalize_selections(selections, nr, nc))
        self.update()
        return None

    def highlights(self) -> SelectionType:
        """Get list of selections as slicable tuples"""
        return self._qtable_view._highlight_model._ranges

    def setHighlights(self, selections: SelectionType):
        """Set list of selections."""
        qtable = self._qtable_view
        qtable.clear_highlights()
        nr, nc = self.tableShape()
        qtable.set_highlights(_normalize_selections(selections, nr, nc))
        self.update()
        return None

    def copyToClipboard(self, headers: bool = True, sep: str = "\t"):
        """Copy currently selected cells to clipboard."""
        selections = self.selections()
        if len(selections) == 0:
            return
        r_ranges = set()
        c_ranges = set()
        for rsel, csel in selections:
            r_ranges.add((rsel.start, rsel.stop))
            c_ranges.add((csel.start, csel.stop))

        nr = len(r_ranges)
        nc = len(c_ranges)
        if nr > 1 and nc > 1:
            raise SelectionRangeError("Cannot copy selected range.")
        else:
            data = self.dataShown()
            if nr == 1:
                axis = 1
            else:
                axis = 0
            ref = pd.concat([data.iloc[sel] for sel in selections], axis=axis)
            ref.to_clipboard(index=headers, header=headers, sep=sep)
        return None

    def _copy_as_literal(self):
        """Copy the selected cells as evaluable string."""
        sels = self.selections()
        if len(sels) == 0:
            raise SelectionRangeError("No selection found.")
        table_stack = self.tableStack()
        i = table_stack.currentIndex()
        viewer = table_stack.parentWidget()._table_viewer
        name = viewer.tables[i].name
        _sl = _selection_to_literal(sels[-1])

        from pandas.io.clipboards import to_clipboard

        return to_clipboard(f"viewer.tables[{name!r}].data.iloc{_sl}", excel=False)

    def pasteFromClipBoard(self):
        raise TableImmutableError("Table is immutable.")

    def readClipBoard(self, sep=r"\s+") -> pd.DataFrame:
        """Read clipboard data and return as pandas DataFrame."""
        return pd.read_clipboard(header=None, sep=sep)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if self._keymap.press_key(e):
            return
        return super().keyPressEvent(e)

    def filter(self) -> FilterType | None:
        """Return the current filter."""
        return self._filter_slice

    @_mgr.interface
    def setFilter(self, sl: FilterType):
        """Set filter to the table view."""
        # NOTE: This method is also called when table needs initialization.

        self._filter_slice = sl
        data_sliced = self.tableSlice()

        if sl is None:
            df_filt = data_sliced
            icon = QtGui.QIcon()
        else:
            try:
                if callable(sl):
                    sl_filt = sl(data_sliced)
                else:
                    sl_filt = sl
                df_filt = data_sliced[sl_filt]

            except Exception as e:
                self.setFilter(None)
                raise ValueError("Error in filter. Filter is reset.") from e
            icon = QColoredSVGIcon.fromfile(ICON_DIR / "filter.svg")

        # update data
        self.model().df = df_filt
        self._filtered_index = df_filt.index
        self._filtered_columns = df_filt.columns

        # update filter icon
        if stack := self.tableStack():
            idx = stack.tableIndex(self)
            bg = self.palette().color(self.backgroundRole())
            whiteness = bg.red() + bg.green() + bg.blue()
            if not icon.isNull() and whiteness <= 128 * 3:
                icon = icon.colored("#FFFFFF")
            stack.setTabIcon(idx, icon)
            if not icon.isNull():
                stack.setIconSize(QtCore.QSize(12, 12))

        return self.refreshTable()

    @setFilter.server
    def setFilter(self, sl: FilterType):
        return (self.filter(),), {}

    @setFilter.set_formatter
    def _setFilter_fmt(self, sl):
        from ....widgets.filtering import ColumnFilter

        if isinstance(sl, ColumnFilter):
            return f"table.filter{sl._repr[2:]}"
        return f"table.filter = {sl!r}"

    @_mgr.interface
    def setForegroundColormap(self, name: str, colormap: Callable | None):
        """Set the colormap for the foreground."""
        if colormap is None:
            self.model()._foreground_colormap.pop(name, None)
        else:
            if not callable(colormap):
                raise TypeError("Cannot use non-callable objects as colormaps.")
            self.model()._foreground_colormap[name] = colormap
        self.refreshTable()
        return None

    @setForegroundColormap.server
    def setForegroundColormap(self, name: str, colormap: Callable):
        cmap = self.model()._foreground_colormap.get(name, None)
        return (name, cmap), {}

    @_mgr.interface
    def setBackgroundColormap(self, name: str, colormap: Callable | None):
        """Set the colormap for the foreground."""
        if colormap is None:
            self.model()._background_colormap.pop(name, None)
        else:
            if not callable(colormap):
                raise TypeError("Cannot use non-callable objects as colormaps.")
            self.model()._background_colormap[name] = colormap
        self.refreshTable()
        return None

    @setBackgroundColormap.server
    def setBackgroundColormap(self, name: str, colormap: Callable):
        cmap = self.model()._background_colormap.get(name, None)
        return (name, cmap), {}

    @_mgr.interface
    def setTextFormatter(self, name: str, fmt: Callable[[Any], str] | str):
        """Set a text formatter function to the column named `name`."""
        if fmt is None:
            self.model()._text_formatter.pop(name, None)
        else:
            if isinstance(fmt, str):
                fmt = fmt.format
            elif not callable(fmt):
                raise TypeError("Text formatter must be a str or a callable object.")
            self.model()._text_formatter[name] = fmt
        self.refreshTable()
        return None

    @setTextFormatter.server
    def setTextFormatter(self, name: str, fmt: Callable[[Any], str] | str):
        fmt = self.model()._text_formatter.get(name, None)
        return (name, fmt), {}

    @_mgr.interface
    def setDataValidator(self, name: str, validator: Callable[[Any], None]):
        """Set a validator function to the column named `name`."""
        if validator is None:
            self.model()._validator.pop(name, None)
        else:
            if not callable(validator):
                raise TypeError("Validator must be callable.")
            self.model()._validator[name] = validator
        self.refreshTable()
        return None

    @setDataValidator.server
    def setDataValidator(self, name: str, validator: Callable[[Any], bool]):
        validator = self.model()._validator.get(name, None)
        return (name, validator), {}

    def setCalculationGraph(self, pos: tuple[int, int], graph: Graph):
        """Set calculation graph at the given position."""
        if graph is None:
            self._qtable_view._ref_graphs.pop(pos)
        else:
            self._set_graph(pos, graph)
        return None

    @_mgr.interface
    def _set_graph(self, pos: tuple[int, int], graph: Graph):
        if graph is None:
            self._qtable_view._ref_graphs.pop(pos, None)
        else:
            self._qtable_view._ref_graphs[pos] = graph
            self._qtable_view._selection_model.set_ranges([graph._destination])
        return None

    @_set_graph.server
    def _set_graph(self, pos: tuple[int, int], graph: Graph):
        graph = self._qtable_view._ref_graphs.get(pos, None)
        return (pos, graph), {}

    @_set_graph.set_formatter
    def _set_graph_fmt(self, pos, graph):
        return repr(graph)

    def refreshTable(self) -> None:
        """Refresh table view."""
        return self._qtable_view._update_all()

    def undoStackView(self, show: bool = True):
        """Show undo stack viewer."""
        out = self._mgr.widget()
        if show:
            self.addSideWidget(out, name="Undo stack")
        return out

    def addSideWidget(self, widget: QtW.QWidget, name: str = ""):
        """Add a widget to the side area of the table."""
        if self._side_area is None:
            from ._side_area import QTableSideArea

            area = QTableSideArea()
            self.addWidget(area)
            self._side_area = area

        self._side_area.addWidget(widget, name=name)
        self.setSizes([500, 200])
        return None

    def addOverlayWidget(
        self,
        widget: QtW.QWidget,
        label: str = "",
        topleft: tuple[int, int] = (0, 0),
    ):
        """Add a widget as an overlay of the table."""
        from ._overlay import QOverlayFrame

        viewport = self._qtable_view.viewport()
        frame = QOverlayFrame(widget, viewport)
        frame.setLabel(label)
        frame.show()

        # if topleft is given as float, interpret as ratio in a cell
        top, left = topleft
        top_int, top_res = divmod(top, 1)
        left_int, left_res = divmod(left, 1)

        index = self._qtable_view.model().index(
            int(round(top_int)), int(round(left_int))
        )

        rect = self._qtable_view.visualRect(index)
        pos = rect.topLeft()
        pos.setX(pos.x() + rect.width() * left_res)
        pos.setY(pos.y() + rect.height() * top_res)
        frame.move(pos)

        size = self._qtable_view.size()
        frame.resize(
            max(frame.width(), int(size.width() * 0.8)),
            max(frame.height(), int(size.height() * 0.8)),
        )
        return None

    def setDualView(self, orientation: str = "horizontal"):
        """Set dual view."""
        from ._table_wrappers import QTableDualView

        if orientation == "vertical":
            qori = Qt.Orientation.Vertical
        elif orientation == "horizontal":
            qori = Qt.Orientation.Horizontal
        else:
            raise ValueError("orientation must be 'vertical' or 'horizontal'.")

        widget0 = self.widget(0)
        if widget0 is not self._central_widget:
            widget0.setParent(None)
            widget0.deleteLater()
        self._central_widget.setParent(None)
        dual = QTableDualView(self._central_widget, qori)
        self.insertWidget(0, dual)
        self._qtable_view.setFocus()
        return dual

    def setPopupView(self):
        """Set splash view."""
        from ._table_wrappers import QTablePopupView

        widget0 = self.widget(0)
        if widget0 is not self._central_widget:
            widget0.setParent(None)
            widget0.deleteLater()
        self._central_widget.setParent(None)
        view = QTablePopupView(self._central_widget)
        self.insertWidget(0, view)
        view.exec()
        return view

    def resetViewMode(self):
        """Reset the view mode to the normal one."""
        widget0 = self.widget(0)
        if widget0 is not self._central_widget:
            widget0.setParent(None)
            self.insertWidget(0, self._central_widget)
            widget0.deleteLater()
        else:
            pass

        return None

    def moveToItem(
        self,
        row: int | None = None,
        column: int | None = None,
        clear_selection: bool = True,
    ):
        """Move current index."""
        selection_model = self._qtable_view._selection_model
        if row is None:
            row = selection_model.current_index.row
        elif row < 0:
            row += self.model().df.shape[0]

        if column is None:
            column = selection_model.current_index.column
        elif column < 0:
            column += self.model().df.shape[1]

        if clear_selection or not (
            selection_model._ctrl_on or selection_model._shift_on
        ):
            selection_model.clear()
        selection_model.move_to(row, column)
        return None

    def tableStack(self) -> QTabbedTableStack | None:
        """Return the table stack."""
        try:
            stack = self.parentWidget().parentWidget()
        except AttributeError:
            stack = None
        if isinstance(stack, QtW.QTabWidget):
            # if a table is used in other widgets, it does not have a table stack
            # as a parent.
            return stack
        return None

    def parentViewer(self) -> _QtMainWidgetBase:
        """Return the parent table viewer."""
        return self._qtable_view.parentViewer()

    def _switch_head_and_index(self, axis: int = 1):
        self.setFilter(None)  # reset filter to avoid unexpected errors
        df = self.model().df
        if axis == 0:
            was_range = isinstance(df.columns, pd.RangeIndex)
            if isinstance(df.index, pd.RangeIndex):  # df[0] to index
                df_new = df.set_index(df.columns[0])
            else:  # index to df[0]
                df_new = df.reset_index()
            if was_range:
                df_new.set_axis(
                    pd.RangeIndex(len(df_new.columns)), axis=1, inplace=True
                )

        elif axis == 1:
            was_range = isinstance(df.index, pd.RangeIndex)
            if isinstance(df.columns, pd.RangeIndex):  # df[0] to column
                top_row = df.iloc[0, :].astype(str)
                df_new = df.iloc[1:, :]
                df_new.set_axis(top_row, axis=1, inplace=True)
            else:  # column to df[0]
                columns = range(len(df.columns))
                head = pd.DataFrame(
                    [
                        pd.Series([x], dtype=dtype)
                        for x, dtype in zip(df.columns, df.dtypes)
                    ],
                    columns=columns,
                )
                df.set_axis(columns, axis=1, inplace=True)
                df_new = pd.concat([head, df], axis=0)
            if was_range:
                df_new.set_axis(pd.RangeIndex(len(df_new)), axis=0, inplace=True)
        else:
            raise ValueError("axis must be 0 or 1.")
        return self.setDataFrame(df_new)

    def _get_ref_expr(self, r: int, c: int) -> str | None:
        """Try to get a reference expression for a cell."""
        graph = self._qtable_view._ref_graphs.get((r, c), None)
        if graph is not None:
            return getattr(graph._func, "expr", None)
        return None

    def _delete_ref_expr(self, r: int, c: int) -> None:
        self._qtable_view._ref_graphs.pop((r, c), None)
        return None

    def _set_forground_colormap_with_dialog(self, index: int):
        from ._colormap import exec_colormap_dialog

        column_name = self._filtered_columns[index]
        if cmap := exec_colormap_dialog(self.getDataFrame()[column_name], self):
            self.setForegroundColormap(column_name, cmap)
        return None

    def _reset_forground_colormap(self, index: int):
        column_name = self._filtered_columns[index]
        return self.setForegroundColormap(column_name, None)

    def _set_background_colormap_with_dialog(self, index: int):
        from ._colormap import exec_colormap_dialog

        column_name = self._filtered_columns[index]
        if cmap := exec_colormap_dialog(self.getDataFrame()[column_name], self):
            self.setBackgroundColormap(column_name, cmap)
        return None

    def _reset_background_colormap(self, index: int):
        column_name = self._filtered_columns[index]
        return self.setBackgroundColormap(column_name, None)

    def _set_text_formatter_with_dialog(self, index: int):
        from ._text_formatter import exec_formatter_dialog

        column_name = self._filtered_columns[index]

        if fmt := exec_formatter_dialog(self.getDataFrame()[column_name], self):
            self.setTextFormatter(column_name, fmt)
        return None

    def _reset_text_formatter(self, index: int) -> None:
        column_name = self._filtered_columns[index]
        return self.setTextFormatter(column_name, None)

    def _delete_selected_highlights(self):
        self._qtable_view._highlight_model.delete_selected()
        self._qtable_view._selection_model.set_ctrl(False)

    def _try_update_console(self):
        viewer = self._qtable_view.parentViewer()
        console = viewer._console_widget
        if console is None or not console.isActive():
            return
        selected = console.selectedText()
        _df = console._current_data_identifier
        if selected.startswith(f"{_df}["):
            sels = self.selections()
            if len(sels) != 1:
                return
            console.setTempText(f"{_df}{_selection_to_literal(sels[0])}")
        return None


class QMutableTable(QBaseTable):
    """A mutable table widget."""

    itemChangedSignal = Signal(ItemInfo)
    rowChangedSignal = Signal(HeaderInfo)
    columnChangedSignal = Signal(HeaderInfo)
    evaluatedSignal = Signal(EvalInfo)
    selectionChangedSignal = Signal()

    _data_raw: pd.DataFrame
    NaN = np.nan

    def __init__(
        self, parent: QtW.QWidget | None = None, data: pd.DataFrame | None = None
    ):
        super().__init__(parent, data)
        self._data_cache = None  # only used in SpreadSheet for now
        self.model().dataEdited.connect(self.setDataFrameValue)

        # header editing signals
        self._qtable_view.horizontalHeader().sectionDoubleClicked.connect(
            self.editHorizontalHeader
        )
        self._qtable_view.verticalHeader().sectionDoubleClicked.connect(
            self.editVerticalHeader
        )
        self._mgr.clear()

        @self.rowChangedSignal.connect
        def _on_row_changed(info: HeaderInfo):
            return self.setVerticalHeaderValue(info.index, info.value)

        @self.columnChangedSignal.connect
        def _on_col_changed(info: HeaderInfo):
            return self.setHorizontalHeaderValue(info.index, info.value)

    def tableShape(self) -> tuple[int, int]:
        """Return the available shape of the table."""
        model = self.model()
        nr = model.rowCount()
        nc = model.columnCount()
        return (nr, nc)

    def tableSlice(self) -> pd.DataFrame:
        """Return 2D table for display."""
        return self._data_raw

    def setDataFrameValue(self, r: _Sliceable, c: _Sliceable, value: Any) -> None:
        """Set `value` at array[r, c]."""
        if not self.isEditable():
            raise TableImmutableError("Table is immutable.")
        data = self._data_raw

        with self._mgr.merging(lambda cmds: self._set_value_fmt(r, c, value)):
            # convert values
            if isinstance(r, slice) and isinstance(c, slice):
                # delete references
                if not self._qtable_view._ref_graphs.is_all_blocked():
                    # this with-block is not needed but make it more efficient
                    if len(self._qtable_view._ref_graphs) < 128:
                        for key in list(self._qtable_view._ref_graphs.keys()):
                            if (
                                r.start <= key[0] < r.stop
                                and c.start <= key[1] < c.stop
                            ):
                                self._set_graph(key, None)

                    else:
                        for _c in range(c.start, c.stop):
                            for _r in range(r.start, r.stop):
                                self._set_graph((_r, _c), None)

                _value: pd.DataFrame = value
                if _value.size == 1:
                    v = _value.values[0, 0]
                    _value = data.iloc[r, c].copy()
                    for _ic, _c in enumerate(range(c.start, c.stop)):
                        _convert_value = self._get_converter(_c)
                        for _ir, _r in enumerate(range(r.start, r.stop)):
                            _value.iloc[_ir, _ic] = _convert_value(_r, _c, v)
                else:
                    for _ic, _c in enumerate(range(c.start, c.stop)):
                        _convert_value = self._get_converter(_c)
                        for _ir, _r in enumerate(range(r.start, r.stop)):
                            _value.iloc[_ir, _ic] = _convert_value(
                                _r, _c, _value.iloc[_ir, _ic]
                            )
                _is_scalar = False
            else:
                self._set_graph((r, c), None)
                _convert_value = self._get_converter(c)
                _value = _convert_value(r, c, value)
                _is_scalar = True

            # if table has filter, indices must be adjusted
            if self._filter_slice is None:
                r0 = r
            else:
                if callable(self._filter_slice):
                    sl = self._filter_slice(data)
                else:
                    sl = self._filter_slice

                spec = np.where(sl)[0].tolist()
                r0 = spec[r]

            _old_value = data.iloc[r0, c]
            if not _is_scalar:
                _old_value: pd.DataFrame
                _old_value = _old_value.copy()  # this is needed for undo

            if self._filter_slice is not None:
                # If table is filtered, the dataframe to be displayed is a different object
                # so we have to update it as well.
                self.model().updateValue(r, c, _value)

            # emit item changed signal if value changed
            if _was_changed(_value, _old_value) and self.isEditable():
                self._set_value(r0, c, r, c, value=_value, old_value=_old_value)

        return None

    @QBaseTable._mgr.undoable
    def _set_value(self, r, c, r_ori, c_ori, value, old_value):
        self.updateValue(r, c, value)
        self._data_cache = None
        self.setSelections([(r_ori, c_ori)])
        self.itemChangedSignal.emit(ItemInfo(r, c, value, old_value))
        return None

    @_set_value.undo_def
    def _set_value(self, r, c, r_ori, c_ori, value, old_value):
        self.updateValue(r, c, old_value)
        self._data_cache = None
        self.setSelections([(r_ori, c_ori)])
        self.itemChangedSignal.emit(ItemInfo(r, c, old_value, value))
        return None

    @_set_value.set_formatter
    def _set_value_fmt(self, r, c, r_ori, c_ori, value, old_value):
        _r = fmt_slice(r)
        _c = fmt_slice(c)
        if isinstance(value, pd.DataFrame):
            if value.size < 6:
                _val = str(value.values.tolist())
            else:
                _val = "..."
        else:
            _val = fmt.map_object(value)
        return f"df.iloc[{_r}, {_c}] = {_val}"

    def assignColumn(self, ds: pd.Series):
        if ds.name in self._data_raw.columns:
            ic = self._data_raw.columns.get_loc(ds.name)
            self.setDataFrameValue(
                slice(0, ds.size), slice(ic, ic + 1), pd.DataFrame(ds)
            )
        else:
            self.assignNewColumn(ds)

    @QBaseTable._mgr.undoable
    def assignNewColumn(self, ds: pd.Series):
        self._data_raw[ds.name] = ds
        self.setDataFrame(self._data_raw)

    @assignNewColumn.undo_def
    def assignNewColumn(self, ds: pd.Series):
        del self._data_raw[ds.name]
        self.setDataFrame(self._data_raw)

    def updateValue(self, r, c, value):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._data_raw.iloc[r, c] = value

        if self._filter_slice is not None:
            self.setFilter(self._filter_slice)
        self.refreshTable()

    def isEditable(self) -> bool:
        """Return the editability of the table."""
        return self.model()._editable

    @QBaseTable._mgr.interface
    def setEditable(self, editable: bool):
        """Set the editability of the table."""
        self.model()._editable = editable
        return None

    @setEditable.server
    def setEditable(self, editable: bool):
        return (self.isEditable(),), {}

    @setEditable.set_formatter
    def _setEditable_fmt(self, editable: bool):
        return f"table.editable = {editable}"

    def toggleEditability(self) -> None:
        """Toggle editability of the table."""
        return self.setEditable(not self.isEditable())

    def connectItemChangedSignal(
        self,
        slot_val: Callable[[ItemInfo], None],
        slot_row: Callable[[HeaderInfo], None],
        slot_col: Callable[[HeaderInfo], None],
        slot_eval: Callable[[EvalInfo], None],
    ) -> None:
        self.itemChangedSignal.connect(slot_val)
        self.rowChangedSignal.connect(slot_row)
        self.columnChangedSignal.connect(slot_col)
        self.evaluatedSignal.connect(slot_eval)
        return None

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        keys = QtKeys(e)
        if not self._keymap.press_key(keys):
            return super().keyPressEvent(e)

    def pasteFromClipBoard(self, sep=r"\s+"):
        """
        Paste data to table.

        This function supports many types of pasting.
        1. Single selection, single data in clipboard -> just paste
        2. Single selection, multiple data in clipboard -> paste starts from the selection position.
        3. Multiple selection, single data in clipboard -> paste the same value for all the selection.
        4. Multiple selection, multiple data in clipboard -> paste only if their shape is identical.

        Also, if data is filtrated, pasted data also follows the filtration.
        """
        selections = self.selections()
        n_selections = len(selections)
        if n_selections == 0:
            return
        elif not self.isEditable():
            return self.tableStack().notifyEditability()
        elif n_selections > 1:
            raise SelectionRangeError("Cannot paste to multiple selections.")

        df = self.readClipBoard(sep=sep)

        # check size and normalize selection slices
        sel = selections[0]
        rrange, crange = sel
        rlen = rrange.stop - rrange.start
        clen = crange.stop - crange.start
        dr, dc = df.shape
        size = dr * dc

        if rlen * clen == 1 and size > 1:
            sel = (
                slice(rrange.start, rrange.start + dr),
                slice(crange.start, crange.start + dc),
            )

        elif size > 1 and (rlen, clen) != (dr, dc):
            # If selection is column-wide or row-wide, resize them
            model = self.model()
            if rlen == model.df.shape[0]:
                rrange = slice(0, dr)
                rlen = dr
            if clen == model.df.shape[1]:
                crange = slice(0, dc)
                clen = dc

            if (rlen, clen) != (dr, dc):
                raise SelectionRangeError(
                    f"Shape mismatch between data in clipboard {(rlen, clen)} and "
                    f"destination {(dr, dc)}."
                )
            else:
                sel = (rrange, crange)

        rsel, csel = sel

        # check dtype
        dtype_src = df.dtypes.values
        dtype_dst = self._data_raw.dtypes.values[csel]
        if any(a.kind != b.kind for a, b in zip(dtype_src, dtype_dst)):
            raise ValueError(
                f"Data type mismatch between data in clipboard {list(dtype_src)} and "
                f"destination {list(dtype_dst)}."
            )

        # update table
        self.setDataFrameValue(rsel, csel, df)
        self.setSelections([sel])

        return None

    def deleteValues(self):
        """Replace selected cells with NaN."""
        if not self.isEditable():
            return None
        selections = self.selections()
        for sel in selections:
            rsel, csel = sel
            nr = rsel.stop - rsel.start
            nc = csel.stop - csel.start
            dtypes = list(self._data_raw.dtypes.values[csel])
            df = pd.DataFrame(
                {
                    c: pd.Series(np.full(nr, self.NaN), dtype=dtypes[c])
                    for c in range(nc)
                },
            )
            self.setDataFrameValue(rsel, csel, df)
        return None

    def editHorizontalHeader(self, index: int) -> QHorizontalHeaderLineEdit:
        """Edit the horizontal header."""
        if not self.isEditable():
            return self.tableStack().notifyEditability()

        qtable = self._qtable_view
        _header = qtable.horizontalHeader()
        return QHorizontalHeaderLineEdit(parent=_header, table=self, pos=(-1, index))

    def editVerticalHeader(self, index: int) -> QVerticalHeaderLineEdit:
        if not self.isEditable():
            return self.tableStack().notifyEditability()

        qtable = self._qtable_view
        _header = qtable.verticalHeader()
        return QVerticalHeaderLineEdit(parent=_header, table=self, pos=(index, -1))

    @QBaseTable._mgr.interface
    def setHorizontalHeaderValue(self, index: int, value: Any) -> None:
        qtable = self._qtable_view
        _header = qtable.horizontalHeader()

        model = self.model()

        colname = model.df.columns[index]
        model.rename_column(colname, value)

        _rename_column(self._data_raw, index, value)
        _rename_column(model.df, index, value)
        self._filtered_columns = _rename_index(self._filtered_columns, index, value)

        # adjust header size
        size_hint = _header.sectionSizeHint(index)
        if _header.sectionSize(index) < size_hint:
            _header.resizeSection(index, size_hint)

        # set selection
        self._qtable_view._selection_model.move_to(-1, index)

        # update
        self.refreshTable()
        return None

    @setHorizontalHeaderValue.server
    def setHorizontalHeaderValue(self, index: int, value: Any) -> Any:
        return (index, self.model().df.columns[index]), {}

    @setHorizontalHeaderValue.set_formatter
    def _setHorizontalHeaderValue_fmt(self, index: int, value: Any) -> Any:
        return f"columns[{index}] = {value!r}"

    @QBaseTable._mgr.interface
    def setVerticalHeaderValue(self, index: int, value: Any) -> None:
        qtable = self._qtable_view
        _header = qtable.verticalHeader()

        _rename_row(self._data_raw, index, value)  # TODO: incompatible with filter
        _rename_row(self.model().df, index, value)
        self._filtered_index = _rename_index(self._filtered_index, index, value)

        # adjust size
        _width_hint = _header.sizeHint().width()
        _header.resize(QtCore.QSize(_width_hint, _header.height()))

        # set selection
        self._qtable_view._selection_model.move_to(index, -1)

        # update
        self.refreshTable()
        return None

    @setVerticalHeaderValue.server
    def setVerticalHeaderValue(self, index: int, value: Any) -> Any:
        return (index, self.model().df.index[index]), {}

    @setVerticalHeaderValue.set_formatter
    def _setVerticalHeaderValue_fmt(self, index: int, value: Any) -> Any:
        return f"index[{index}] = {value!r}"

    def undo(self) -> Any:
        """Undo last operation."""
        return self._mgr.undo()

    def redo(self) -> Any:
        """Redo last undo operation."""
        return self._mgr.redo()


class QMutableSimpleTable(QMutableTable):
    """A mutable table with a single QTableView."""

    @property
    def _qtable_view(self) -> _QTableViewEnhanced:
        return self._qtable_view_

    def createQTableView(self):
        from ._enhanced_table import _QTableViewEnhanced

        self._qtable_view_ = _QTableViewEnhanced(self)
        self.addWidget(self._qtable_view_)
        return None


def _was_changed(val: Any, old_val: Any) -> bool:
    # NOTE pd.NA == x returns pd.NA, not False
    out = False
    if isinstance(val, pd.DataFrame):
        out = True

    elif isna(val):
        if not isna(old_val):
            out = True
    else:
        if isna(old_val) or val != old_val:
            out = True
    return out


def _normalize_selections(
    selections: SelectionType, nr: int, nc: int
) -> list[tuple[slice, slice]]:
    _new_selections: list[tuple[slice, slice]] = []
    for sel in selections:
        r, c = sel
        # if int is used instead of slice
        r = _normalize_one(r, nr)
        c = _normalize_one(c, nc)
        _new_selections.append((r, c))
    return _new_selections


def _normalize_one(r, nr: int) -> slice:
    if not isinstance(r, slice):
        _r = r.__index__()
        if _r < 0:
            _r += nr
        r = slice(_r, _r + 1)
    else:
        start, stop, step = r.indices(nr)
        if step != 1:
            raise ValueError("step must be 1")
        r = slice(start, stop)
    return r


def _rename_row(df: pd.DataFrame, idx: int, new_name: str) -> None:
    """Rename row label at the given index."""
    rowname = df.index[idx]
    df.rename(index={rowname: new_name}, inplace=True)
    return None


def _rename_column(df: pd.DataFrame, idx: int, new_name: str) -> None:
    """Rename column label at the given index."""
    colname = df.columns[idx]
    df.rename(columns={colname: new_name}, inplace=True)
    return None


def _rename_index(di: pd.Index | None, idx: int, new_name: str) -> pd.Index:
    if di is None:
        return di
    di_list = list(di)
    di_list[idx] = new_name
    return pd.Index(di_list)


def _fmt_slice(sl: slice) -> str:
    return f"{sl.start}:{sl.stop}"


def _selection_to_literal(sel: tuple[slice, slice]) -> str:
    rsel, csel = sel
    rsize = rsel.stop - rsel.start
    csize = csel.stop - csel.start
    if rsize == 1 and csize == 1:
        txt = f"[{rsel.start}, {csel.start}]"
    elif rsize == 1:
        txt = f"[{rsel.start}, {_fmt_slice(csel)}]"
    elif csize == 1:
        txt = f"[{_fmt_slice(rsel)}, {csel.start}]"
    else:
        txt = f"[{_fmt_slice(rsel)}, {_fmt_slice(csel)}]"
    return txt


_V = TypeVar("_V")


def _convert_value(
    r: int,
    c: int,
    x: str,
    validator: Callable[[_V], bool],
    converter: Callable[[int, int, str], _V],
) -> _V:
    """Convert value with validation."""
    val = converter(r, c, x)  # convert value first
    validator(val)  # Raise error if invalid
    return val
