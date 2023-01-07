from __future__ import annotations

import logging
from functools import partial
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING, Iterable, Tuple, TypeVar, overload
import warnings
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Signal, Qt

import numpy as np
import pandas as pd
from collections_undo import fmt, arguments

from ._item_model import AbstractDataFrameModel
from ._line_edit import (
    QHorizontalHeaderLineEdit,
    QVerticalHeaderLineEdit,
    QCellLiteralEdit,
)
from tabulous._sort_filter_proxy import SortFilterProxy
from tabulous._dtype import isna
from tabulous._qt._undo import QtUndoManager, fmt_slice
from tabulous._qt._svg import QColoredSVGIcon
from tabulous._keymap import QtKeys, QtKeyMap
from tabulous._qt._action_registry import QActionRegistry
from tabulous.types import ProxyType, ItemInfo, HeaderInfo, EvalInfo
from tabulous.exceptions import (
    SelectionRangeError,
    TableImmutableError,
    UnreachableError,
)
from tabulous._pd_index import as_not_ranged, as_constructor, is_ranged

if TYPE_CHECKING:
    from ._delegate import TableItemDelegate
    from ._side_area import QTableSideArea
    from ._enhanced_table import _QTableViewEnhanced
    from tabulous._qt._table_stack import QTabbedTableStack
    from tabulous._qt._mainwindow import _QtMainWidgetBase
    from tabulous.types import SelectionType, _Sliceable
    from tabulous._psygnal import InCellRangedSlot

logger = logging.getLogger("tabulous")
ICON_DIR = Path(__file__).parent.parent.parent / "_icons"

_SplitterStyle = """
QSplitter::handle {
    background-color: gray;
    border: 0px;
    height: 2px;
    margin-left: 5px;
    margin-right: 5px;
    border-radius: 1px;
}
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

        self._proxy = SortFilterProxy()
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

    def setOrientation(self, a0: Qt.Orientation) -> None:
        """Set table orientation and the side area orientation."""
        a1 = 1 - a0  # opposite orientation
        super().setOrientation(a0)
        if self._side_area is not None:
            self._side_area.setOrientation(a1)
        return None

    def createHandle(self) -> QTableHandle:
        """Create custom handle."""
        return QTableHandle(Qt.Orientation.Horizontal, self)

    def showContextMenu(self, pos: QtCore.QPoint) -> None:
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
                sel_model.current_index = (row, col)
                self.setSelections([(row, col)])
            highlight_model.select([])

        return self.execContextMenu(
            self._qtable_view.viewport().mapToGlobal(pos), (row, col)
        )

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

    # fmt: off
    @overload
    def _get_sub_frame(self, columns: list[str]) -> pd.DataFrame: ...
    @overload
    def _get_sub_frame(self, columns: str) -> pd.Series: ...
    # fmt: on

    def _get_sub_frame(self, columns):
        return self.getDataFrame()[columns]

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
        """Shape of the visible data"""
        return self.tableShape()

    def dataShapeRaw(self) -> tuple[int, int]:
        return self.getDataFrame().shape

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

    def setLabeledData(self, row, col, value) -> None:
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

    def assignColumns(self, serieses: list[pd.Series]) -> None:
        raise TableImmutableError("Table is immutable.")

    def convertValue(self, c: int, value: Any) -> Any:
        """Convert value before updating DataFrame."""
        return value

    def _get_converter(self, c: int) -> Callable[[Any, Any], Any]:
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

    def selections(self, map: bool = False) -> SelectionType:
        """Get list of selections as slicable tuples"""
        ranges = self._qtable_view._selection_model.as_ranges()
        if not map:
            return ranges
        return [
            (self._proxy.get_source_slice(r, force_single_row=True), c)
            for r, c in ranges
        ]

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
        return self._qtable_view._highlight_model.as_ranges()

    @_mgr.interface
    def setHighlights(self, selections: SelectionType):
        """Set list of selections."""
        qtable = self._qtable_view
        qtable.clear_highlights()
        nr, nc = self.tableShape()
        qtable.set_highlights(_normalize_selections(selections, nr, nc))
        self.update()
        return None

    @setHighlights.server
    def setHighlights(self, selections: SelectionType):
        return arguments(self.highlights())

    def _selected_dataframe(self) -> pd.DataFrame:
        """Currently selected cells as a data frame."""
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
        data = self.dataShown()
        if nr == 1:
            axis = 1
        else:
            axis = 0
        ref = pd.concat([data.iloc[sel] for sel in selections], axis=axis)
        return ref

    def copyToClipboard(self, headers: bool = True, sep: str = "\t") -> None:
        """Copy currently selected cells to clipboard."""
        ref = self._selected_dataframe()
        ref.to_clipboard(index=headers, header=headers, sep=sep)
        return None

    def _copy_as_literal(self):
        """Copy the selected cells as evaluable string."""
        sels = self.selections()
        if len(sels) == 0:
            raise SelectionRangeError("No selection found.")
        table_stack = self.tableStack()
        if table_stack is None:
            raise ValueError("Table is not in a table stack.")
        i = table_stack.currentIndex()
        viewer = table_stack.parentWidget()._table_viewer
        name = viewer.tables[i].name
        _sl = _selection_to_literal(sels[-1])
        return _to_clipboard(f"viewer.tables[{name!r}].data.iloc{_sl}", excel=False)

    def _copy_as_formated(self, format: str = "markdown"):
        """Copy the selected cells as markdown format."""
        ref = self._selected_dataframe()
        index = not is_ranged(ref.index)
        if format == "markdown":
            s = _tabulate(ref, tablefmt="github", index=index)
        elif format == "latex":
            s = ref.to_latex(index=index)
        elif format == "html":
            s = ref.to_html(index=index)
        elif format == "rst":
            s = _tabulate(ref, tablefmt="rst", index=index)
        elif format == "grid":
            s = _dataframe_to_grid_table(ref)
        else:
            raise ValueError(f"Unknown format: {format!r}")
        return _to_clipboard(s, excel=False)

    def _copy_as_new_table(self, type_: str = "same"):
        """Copy the selected range to a new table."""
        sels = self.selections()
        if len(sels) != 1:
            raise SelectionRangeError("Inappropriate selection range.")

        table_stack = self.tableStack()
        if table_stack is None:
            raise ValueError("Table is not in a table stack.")
        i = table_stack.currentIndex()
        viewer = table_stack.parentWidget()._table_viewer
        name = viewer.tables[i].name

        df_cropped = self.getDataFrame().iloc[sels[0]]
        if type_ == "table":
            viewer.add_table(df_cropped, name=f"{name}-cropped", copy=False)
        elif type_ == "spreadsheet":
            viewer.add_spreadsheet(df_cropped, name=f"{name}-cropped", copy=False)
        elif type_ == "same":
            if viewer.tables[i].table_type == "SpreadSheet":
                viewer.add_spreadsheet(df_cropped, name=f"{name}-cropped", copy=False)
            else:
                viewer.add_table(df_cropped, name=f"{name}-cropped", copy=False)
        else:
            raise RuntimeError(f"Unknown type: {type_!r}")

    def pasteFromClipBoard(self):
        raise TableImmutableError("Table is immutable.")

    def readClipBoard(self, sep=r"\s+") -> pd.DataFrame:
        """Read clipboard data and return as pandas DataFrame."""
        return pd.read_clipboard(header=None, sep=sep)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if self._keymap.press_key(e):
            return None
        return super().keyPressEvent(e)

    def proxy(self) -> SortFilterProxy:
        """The sort/filter proxy object."""
        return self._proxy

    def setProxy(self, proxy: ProxyType, clear_header_widgets: bool = True):
        """Set sort/filter to the table view."""
        with self._mgr.merging(lambda cmds: f"table.proxy = {proxy!r}"):
            if clear_header_widgets:
                self.updateHorizontalHeaderWidget({})
            self._set_proxy(proxy)
        return None

    @_mgr.interface
    def _set_proxy(self, proxy: ProxyType):
        # NOTE: This method is also called when table needs initialization.
        self._proxy = SortFilterProxy(proxy)
        try:
            df_filt = self._apply_proxy()
        except Exception as e:
            # To avoid continuous error, set proxy to None.
            self._set_proxy(None)
            raise e

        prx = self._proxy
        proxy_type = prx.proxy_type
        if proxy_type == "none":
            icon = QtGui.QIcon()
        elif proxy_type == "filter":
            icon = QColoredSVGIcon.fromfile(ICON_DIR / "filter.svg")
        elif proxy_type == "sort":
            icon = QColoredSVGIcon.fromfile(ICON_DIR / "sort_table.svg")
        else:
            raise RuntimeError(f"Unknown proxy type: {proxy_type!r}")

        # update data
        self.model().df = df_filt
        self._filtered_index = df_filt.index
        self._filtered_columns = df_filt.columns

        # update filter icon
        if stack := self.tableStack():
            idx = stack.tableIndex(self)
            bg = self.palette().color(self.backgroundRole())
            whiteness = bg.red() + bg.green() + bg.blue()
            if not icon.isNull():
                if whiteness <= 128 * 3:
                    icon = icon.colored("#CCCCCC")
                else:
                    icon = icon.colored("#1E1E1E")

            stack.setTabIcon(idx, icon)
            if not icon.isNull():
                stack.setIconSize(QtCore.QSize(12, 12))

        return self.refreshTable()

    def _apply_proxy(self):
        data_sliced = self.tableSlice()
        return self._proxy.apply(data_sliced)

    @_set_proxy.server
    def _set_proxy(self, proxy: ProxyType):
        return arguments(self.proxy())

    @_set_proxy.set_formatter
    def _set_proxy_fmt(self, proxy: ProxyType):
        return f"table.proxy.set({proxy!r})"

    @_mgr.interface
    def setHorizontalHeaderWidget(self, idx: int, widget: QtW.QWidget | None):
        hheader = self._qtable_view.horizontalHeader()
        if widget is None:
            hheader.removeSectionWidget(idx)
        else:
            hheader.setSectionWidget(idx, widget)

    @setHorizontalHeaderWidget.server
    def setHorizontalHeaderWidget(self, idx: int, widget: QtW.QWidget | None):
        hheader = self._qtable_view.horizontalHeader()
        return arguments(idx, hheader.sectionWidget(idx))

    @_mgr.interface
    def updateHorizontalHeaderWidget(self, d: dict[int, QtW.QWidget] = {}):
        """Update horizontal header widgets."""
        hheader = self._qtable_view.horizontalHeader()
        hheader.removeSectionWidget()
        for idx, widget in d.items():
            hheader.setSectionWidget(idx, widget)

    @updateHorizontalHeaderWidget.server
    def updateHorizontalHeaderWidget(self, d: dict[int, QtW.QWidget]):
        hheader = self._qtable_view.horizontalHeader()
        return arguments(hheader._header_widgets.copy())

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
        return arguments(name, cmap)

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
        return arguments(name, cmap)

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
        return arguments(name, fmt)

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
        return arguments(name, validator)

    def itemLabel(self, r: int, c: int):
        model = self.model()
        if content := model._decorations.get((r, c), None):
            return content[1]
        return None

    @_mgr.interface
    def setItemLabel(self, r: int, c: int, text: str | None):
        model = self.model()
        index = model.index(r, c)
        return model.set_cell_label(index, text)

    @setItemLabel.server
    def setItemLabel(self, r: int, c: int, text: str):
        return arguments(r, c, self.itemLabel(r, c))

    def setInCellSlot(self, pos: tuple[int, int], slot: InCellRangedSlot):
        """Set in-cell slot at the given position."""
        if slot is None:
            self._qtable_view._table_map.pop(pos)
        else:
            self._set_incell_slot(pos, slot)
        return None

    @_mgr.interface
    def _set_incell_slot(self, pos: tuple[int, int], slot: InCellRangedSlot):
        """Set in-cell slot at the given position undoably."""
        if slot is None:
            self._qtable_view._table_map.pop(pos, None)
        else:
            self._qtable_view._table_map[pos] = slot
            if dest := slot.last_destination:
                self._qtable_view._selection_model.set_ranges([dest])
        return None

    @_set_incell_slot.server
    def _set_incell_slot(self, pos: tuple[int, int], slot: InCellRangedSlot):
        slot = self._qtable_view._table_map.get(pos, None)
        return arguments(pos, slot)

    @_set_incell_slot.set_formatter
    def _set_incell_slot_fmt(self, pos, slot: InCellRangedSlot):
        return f"table.cell[{pos[0]}, {pos[1]}] = '&={slot.as_literal()}'"

    def refreshTable(self, process: bool = False) -> None:
        """Refresh table view."""
        self._qtable_view._update_all()
        if process:
            QtW.QApplication.processEvents()
        return None

    def undoStackView(self, show: bool = True):
        """Show undo stack viewer."""
        out = self._mgr.widget()
        if show:
            self.addSideWidget(out, name="Undo stack")
        return out

    def addSideWidget(self, widget: QtW.QWidget, name: str = "") -> None:
        """Add a widget to the side area of the table."""
        if self._side_area is None:
            from ._side_area import QTableSideArea

            area = QTableSideArea()
            self.addWidget(area)
            self._side_area = area
            self.setOrientation(self.orientation())

        self._side_area.addWidget(widget, name=name)
        self.setSizes([500, 200])
        return None

    def addOverlayWidget(
        self,
        widget: QtW.QWidget,
        label: str = "",
        topleft: tuple[float, float] = (0, 0),
        size: tuple[float, float] | None = None,
        grip: bool = True,
    ) -> None:
        """Add a widget as an overlay of the table."""
        from ._overlay import QOverlayFrame

        viewport = self._qtable_view.viewport()
        frame = QOverlayFrame(widget, viewport, grip=grip)
        frame.setLabel(label)
        frame.show()

        # if topleft is given as float, interpret as ratio in a cell
        top, left = topleft
        top_int, top_res = divmod(top, 1)
        left_int, left_res = divmod(left, 1)
        top_int = int(round(top_int))
        left_int = int(round(left_int))

        index_tl = self._qtable_view.model().index(top_int, left_int)

        rect_tl = self._qtable_view.visualRect(index_tl)
        pos = rect_tl.topLeft()
        pos.setX(pos.x() + rect_tl.width() * left_res)
        pos.setY(pos.y() + rect_tl.height() * top_res)
        frame.move(pos)

        table_size = self._qtable_view.size()
        if size is None:
            frame.resize(
                max(frame.width(), int(table_size.width() * 0.8)),
                max(frame.height(), int(table_size.height() * 0.8)),
            )
        else:
            width, height = size
            bottom_int, bottom_res = divmod(top + height - 1, 1)
            right_int, right_res = divmod(left + width - 1, 1)
            bottom_int = int(round(bottom_int))
            right_int = int(round(right_int))

            index_br = self._qtable_view.model().index(bottom_int, right_int)

            rect_br = self._qtable_view.visualRect(index_br)
            _w = rect_br.width() * right_res
            _h = rect_br.height() * bottom_res
            rect_br.setBottom(rect_br.bottom() + _h)
            rect_br.setRight(rect_br.right() + _w)
            rect = rect_tl.united(rect_br)
            frame.resize(rect.size())

        return frame

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

    def resetViewMode(self) -> None:
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
    ) -> None:
        """Move current index."""
        selection_model = self._qtable_view._selection_model
        df_shape = self.model().df.shape
        table_shape = self.model().rowCount(), self.model().columnCount()

        if row is None:
            row = selection_model.current_index.row
        elif row < 0:
            if row == -1 and df_shape[0] - 1 <= selection_model.current_index.row:
                row += table_shape[0]
            else:
                row += df_shape[0]

        if column is None:
            column = selection_model.current_index.column
        elif column < 0:
            if column == -1 and df_shape[1] - 1 <= selection_model.current_index.column:
                column += table_shape[1]
            else:
                column += df_shape[1]

        # If selection is not going to be expanded, clear the selection first.
        if clear_selection or not (
            selection_model._ctrl_on or selection_model._shift_on
        ):
            selection_model.clear()

        selection_model.move_to(row, column)
        return None

    def showContextMenuAtIndex(self):
        """Programmatically show context menu at index (r, c)."""
        r, c = self._qtable_view._selection_model.current_index
        if r >= 0 and c >= 0:
            index = self._qtable_view.model().index(r, c)
            rect = self._qtable_view.visualRect(index)
            self.showContextMenu(rect.center())
        elif r < 0:
            header = self._qtable_view.horizontalHeader()
            rect = header.visualRectAtIndex(c)
            header._show_context_menu(rect.center())
        elif c < 0:
            header = self._qtable_view.verticalHeader()
            rect = header.visualRectAtIndex(r)
            header._show_context_menu(rect.center())
        else:
            raise RuntimeError("Invalid index")

    def raiseSlotError(self):
        qtable_view = self._qtable_view
        idx = qtable_view._selection_model.current_index
        if slot := qtable_view._table_map.get_by_dest(idx, None):
            if slot._current_error is not None:
                slot.raise_in_msgbox()

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

    def _switch_head_and_index(self, axis: int = 1) -> None:
        """Switch the first row/column data and the index object."""
        self.setProxy(None)  # reset filter to avoid unexpected errors
        df = self.model().df
        if axis == 0:
            was_range = is_ranged(df.columns)
            if is_ranged(df.index):  # df[0] to index
                df_new = df.set_index(df.columns[0])
            else:  # index to df[0]
                df_new = df.reset_index()
            if was_range:
                _index = as_constructor(df.columns)(df.columns.size)
                df_new.set_axis(_index, axis=1, inplace=True)

        elif axis == 1:
            was_range = is_ranged(df.index)
            if is_ranged(df.columns):  # df[0] to column
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
        """Try to get a reference expression for the cell at (r, c)."""
        r = self._proxy.get_source_index(r)
        if slot := self._qtable_view._table_map.get((r, c), None):
            return slot.as_literal()
        return None

    def _get_ref_expr_by_dest(self, r: int, c: int) -> str | None:
        """Try to get a reference expression for the cell at (r, c)."""
        r = self._proxy.get_source_index(r)
        if slot := self._qtable_view._table_map.get_by_dest((r, c), None):
            return slot.as_literal()
        return None

    def _delete_selected_highlights(self) -> None:
        """Delete the selected highlight."""
        self._qtable_view._highlight_model.delete_selected()
        self._qtable_view._selection_model.set_ctrl(False)
        return None

    def _header_widgets(self) -> dict[int, QtW.QWidget]:
        """Return the header widgets."""
        return self._qtable_view.horizontalHeader()._header_widgets


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

        with self._mgr.merging(lambda _: self._set_value_fmt(r, c, value)):
            # convert values
            if isinstance(r, slice) and isinstance(c, slice):
                # delete references
                self._clear_incell_slots(r, c)
                _value = self._pre_set_array(r, c, value)
                _is_scalar = False
            else:
                self._set_incell_slot((r, c), None)
                _convert_value = self._get_converter(c)
                _value = _convert_value(c, value)
                _is_scalar = True

            # if table has proxy, indices must be adjusted
            r0 = self._get_proxy_source_index(r)

            _old_value = data.iloc[r0, c]
            if not _is_scalar:
                _old_value: pd.DataFrame
                _old_value = _old_value.copy()  # this is needed for undo

            if self._proxy.proxy_type != "none":
                # If table is filtered, the dataframe to be displayed is a different
                # object so we have to update it as well.
                self.model().updateValue(r, c, _value)

            # emit item changed signal if value changed
            if _was_changed(_value, _old_value) and self.isEditable():
                self._set_value(r0, c, r, c, value=_value, old_value=_old_value)

        return None

    def _clear_incell_slots(self, r: slice, c: slice) -> None:
        # this with-block is not needed but make it more efficient
        if len(self._qtable_view._table_map) < 128:
            for key in list(self._qtable_view._table_map.keys()):
                if r.start <= key[0] < r.stop and c.start <= key[1] < c.stop:
                    self._set_incell_slot(key, None)

        else:
            for _c in range(c.start, c.stop):
                for _r in range(r.start, r.stop):
                    self._set_incell_slot((_r, _c), None)
        return None

    def setLabeledData(self, r: slice, c: slice, value: pd.Series):
        """Set 1D data with index as labels."""

        if not self.isEditable():
            raise TableImmutableError("Table is immutable.")
        if c.stop != c.start + 1:
            raise ValueError("Only one column can be set at a time.")
        data = self._data_raw

        with self._mgr.merging(lambda _: self._set_value_fmt(r, c, value)):
            # delete references
            self._clear_incell_slots(r, c)

            _value = self._pre_set_array(r, c, pd.DataFrame(value))

            # if table has proxy, indices must be adjusted
            r0 = self._get_proxy_source_index(r)

            _old_value = data.iloc[r0, c].copy()  # this is needed for undo

            if self._proxy is not None:
                # If table is filtered, the dataframe to be displayed is a different
                # object so we have to update it as well.
                self.model().updateValue(r, c, _value)

            # emit item changed signal if value changed
            if _was_changed(_value, _old_value) and self.isEditable():
                self._set_value(r0, c, r, c, value=_value, old_value=_old_value)
                if isinstance(r0, slice):
                    _iter = range(r0.start, r0.stop)
                elif isinstance(r0, np.ndarray):
                    _iter = r0
                else:
                    raise UnreachableError(f"{type(r0)!r}.")
                for _i, _r in enumerate(_iter):
                    self.setItemLabel(_r, c.start, value.index[_i])
        return None

    def _get_proxy_source_index(self, r: int | slice):
        return self._proxy.get_source_index(r)

    def _pre_set_array(self, r: slice, c: slice, _value: pd.DataFrame):
        """Convert input dataframe for setting to data[r, c]."""
        if _value.size == 1:
            v = _value.values[0, 0]
            _value = self._data_raw.iloc[r, c].copy()
            for _ic, _c in enumerate(range(c.start, c.stop)):
                _convert_value = self._get_converter(_c)
                for _ir, _r in enumerate(range(r.start, r.stop)):
                    _value.iloc[_ir, _ic] = _convert_value(_c, v)
        else:
            for _ic, _c in enumerate(range(c.start, c.stop)):
                _convert_value = self._get_converter(_c)
                for _ir, _r in enumerate(range(r.start, r.stop)):
                    _value.iloc[_ir, _ic] = _convert_value(_c, _value.iloc[_ir, _ic])
        return _value

    @QBaseTable._mgr.undoable
    def _set_value(self, r, c, r_ori, c_ori, value, old_value):
        """Undoable set-value function."""
        self.updateValue(r, c, value)
        self._data_cache = None
        # update selection using the non-filtered index.
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

    @_set_value.reduce_rule
    def _set_value_reduce(self, args_old, args_new):
        # r, c, r_ori, c_ori, value, old_value
        r = args_new["r"]
        c = args_new["c"]
        r_ori = args_new["r_ori"]
        c_ori = args_new["c_ori"]
        value = args_new["value"]
        old_value = args_old["old_value"]
        return arguments(r, c, r_ori, c_ori, value, old_value)

    def updateValue(self, r, c, value):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._data_raw.iloc[r, c] = value

        if self._proxy.proxy_type != "none":
            self._set_proxy(self._proxy)
        return self.refreshTable()

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
        return arguments(self.isEditable())

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

    def _paste_data(self, df: pd.DataFrame):
        """Paste data to the table."""
        selections = self.selections()
        n_selections = len(selections)
        if n_selections == 0:
            return
        elif not self.isEditable():
            if stack := self.tableStack():
                stack.notifyEditability()
            return None
        elif n_selections > 1:
            raise SelectionRangeError("Cannot paste to multiple selections.")

        dr, dc = df.shape

        # check size and normalize selection slices
        sel = selections[0]
        rrange, crange = sel
        rstart = 0 if rrange.start is None else rrange.start
        rstop = rstart + dr if rrange.stop is None else rrange.stop
        cstart = 0 if crange.start is None else crange.start
        cstop = cstart + dc if crange.stop is None else crange.stop
        rrange = slice(rstart, rstop)
        crange = slice(cstart, cstop)
        sel = (rrange, crange)

        # check if the selection is valid
        rlen = rstop - rstart
        clen = cstop - cstart
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

    def pasteFromClipBoard(self, sep=r"\s+"):
        """
        Paste data to table.

        This function supports many types of pasting.
        1. Single selection, single data in clipboard -> just paste
        2. Single selection, multiple data in clipboard -> paste starts from the
           selection position.
        3. Multiple selection, single data in clipboard -> paste the same value for
           all the selection.
        4. Multiple selection, multiple data in clipboard -> paste only if their
           shape is identical.

        Also, if data is filtrated, pasted data also follows the filtration.
        """
        df = self.readClipBoard(sep=sep)
        if df.shape == (1, 1) and QCellLiteralEdit._is_eval_like(str(df.iat[0, 0])):
            sels = self.selections()
            if len(sels) != 1:
                raise SelectionRangeError(
                    "Multiple ranges are selected. Failed to paste."
                )
            sel = sels[0]
            rsel, csel = sel
            if None in (rsel.start, rsel.stop, csel.start, csel.stop):
                raise SelectionRangeError("Selection is not valid. Failed to paste.")
            if rsel.stop - rsel.start == 1 and csel.stop - csel.start == 1:
                # single cell selection
                editor = self._qtable_view._edit_current()
                editor.setText(df.iat[0, 0])

        return self._paste_data(df)

    def deleteValues(self):
        """Replace selected cells with NaN."""
        if not self.isEditable():
            return None
        selections = self.selections()
        rsize, csize = self._data_raw.shape
        for sel in selections:
            # normalize selection range to non-None slices
            rsel, csel = sel
            rstart = 0 if rsel.start is None else rsel.start
            rstop = rsize if rsel.stop is None else rsel.stop
            cstart = 0 if csel.start is None else csel.start
            cstop = csize if csel.stop is None else csel.stop
            rsel = slice(rstart, rstop)
            csel = slice(cstart, cstop)

            nr = rstop - rstart
            nc = cstop - cstart
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
            if stack := self.tableStack():
                stack.notifyEditability()
            return None

        qtable = self._qtable_view
        _header = qtable.horizontalHeader()
        return QHorizontalHeaderLineEdit(parent=_header, table=self, pos=(-1, index))

    def editVerticalHeader(self, index: int) -> QVerticalHeaderLineEdit:
        """Edit the vertical header."""
        if not self.isEditable():
            if stack := self.tableStack():
                stack.notifyEditability()
            return None

        qtable = self._qtable_view
        _header = qtable.verticalHeader()
        return QVerticalHeaderLineEdit(parent=_header, table=self, pos=(index, -1))

    def setHorizontalHeaderValue(self, index: int, value: Any) -> None:
        return self._set_horizontal_header_value(index, value, constructor=None)

    @QBaseTable._mgr.interface
    def _set_horizontal_header_value(self, index: int, value, constructor=None):
        qtable = self._qtable_view
        _header = qtable.horizontalHeader()

        model = self.model()

        colname = model.df.columns[index]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.rename_column(colname, value)

            _rename_column(model.df, index, value)
            self._filtered_columns = _rename_index(self._filtered_columns, index, value)
            if constructor is None:
                _rename_column(self._data_raw, index, value)
            else:
                self._data_raw.columns = constructor(self._data_raw.columns.size)

        # adjust header size
        size_hint = _header.sectionSizeHint(index)
        if _header.sectionSize(index) < size_hint:
            _header.resizeSection(index, size_hint)

        # set selection
        self._qtable_view._selection_model.move_to(-1, index)

        # update
        self.refreshTable()
        return None

    @_set_horizontal_header_value.server
    def _set_horizontal_header_value(self, index: int, value: Any, constructor) -> Any:
        return arguments(
            index,
            self.model().df.columns[index],
            constructor=as_constructor(self._data_raw.columns),
        )

    @_set_horizontal_header_value.set_formatter
    def _set_horizontal_header_value_fmt(self, index: int, value, constructor):
        return f"table.columns[{index}] = {value!r}"

    def setVerticalHeaderValue(self, index: int, value: Any) -> None:
        return self._set_vertical_header_value(index, value, constructor=None)

    @QBaseTable._mgr.interface
    def _set_vertical_header_value(self, index: int, value, constructor=None):
        qtable = self._qtable_view
        _header = qtable.verticalHeader()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _rename_row(self.model().df, index, value)
            r0 = self._get_proxy_source_index(index)
            self._filtered_index = _rename_index(self._filtered_index, r0, value)
            if constructor is None:
                _rename_row(self._data_raw, r0, value)
            else:
                self._data_raw.index = constructor(self._data_raw.index.size)

        # adjust size
        _width_hint = _header.sizeHint().width()
        _header.resize(QtCore.QSize(_width_hint, _header.height()))

        # set selection
        self._qtable_view._selection_model.move_to(index, -1)

        # update
        self.refreshTable()
        return None

    @_set_vertical_header_value.server
    def _set_vertical_header_value(self, index: int, value: Any, constructor):
        return arguments(
            index,
            self.model().df.index[index],
            constructor=as_constructor(self._data_raw.index),
        )

    @_set_vertical_header_value.set_formatter
    def _set_vertical_header_value_fmt(self, index: int, value, constructor):
        return f"table.index[{index}] = {value!r}"

    def undo(self) -> Any:
        """Undo last operation."""
        return self._mgr.undo()

    def redo(self) -> Any:
        """Redo last undo operation."""
        return self._mgr.redo()

    @staticmethod
    def _set_value_fmt(r, c, value):
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


class QMutableSimpleTable(QMutableTable):
    """A mutable table with a single QTableView."""

    def dataShapeRaw(self) -> tuple[int, int]:
        return self._data_raw.shape

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
    as_not_ranged(df.columns)
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
    c: int,
    x: str,
    validator: Callable[[_V], bool],
    converter: Callable[[int, int, str], _V],
) -> _V:
    """Convert value with validation."""
    val = converter(c, x)  # convert value first
    validator(val)  # Raise error if invalid
    return val


def _to_clipboard(s: str, excel: bool = True, **kwargs) -> None:
    """Copy dataframe to clipboard."""
    from pandas.io.clipboards import to_clipboard

    return to_clipboard(s, excel=excel, **kwargs)


def _tabulate(df: pd.DataFrame, tablefmt: str, index: bool = False) -> str:
    try:
        from tabulate import tabulate
    except ImportError:
        raise ImportError("No module named 'tabulate'. Please `pip install tabulate`.")

    return tabulate(
        df.astype("string").fillna(""),
        headers="keys",
        tablefmt=tablefmt,
        showindex=index,
    )


def _dataframe_to_grid_table(df: pd.DataFrame):
    cell_width = [col.str.len().max() for _, col in df.items()]

    def table_div(sep="-"):
        return "".join("+" + (width + 2) * sep for width in cell_width) + "+"

    def row_to_str(row: Iterable[str]):
        return "| " + " | ".join([f"{x:{w}}" for x, w in zip(row, cell_width)]) + " |"

    lines = [table_div(), row_to_str(df.columns), table_div("=")]
    for _, row in df.iterrows():
        lines.append(row_to_str(row))
        lines.append(table_div())
    return "\n".join(lines)
