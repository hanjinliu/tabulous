from __future__ import annotations
from typing import Any, Callable, NamedTuple, TYPE_CHECKING
import weakref
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Signal, Qt

from ._utils import show_messagebox

if TYPE_CHECKING:
    import pandas as pd


class ItemInfo(NamedTuple):
    row: int
    column: int
    value: Any
    updated: bool

_EDITABLE = QtW.QTableWidget.EditKeyPressed | QtW.QTableWidget.DoubleClicked
_READ_ONLY = QtW.QTableWidget.NoEditTriggers

class QTableLayer(QtW.QTableWidget):
    itemChangedSignal = Signal(ItemInfo)
    selectionChangedSignal = Signal(list)
    
    def __init__(self, parent=None, data: pd.DataFrame = None):
        self._data_ref: weakref.ReferenceType[pd.DataFrame] = weakref.ref(data)
        super().__init__(*data.shape, parent)
        delegate = TableItemDelegate(parent=self)
        self.setItemDelegate(delegate)
        delegate.edited.connect(lambda x: self.itemChangedSignal.emit(self._update_data(*x)))
        self._editable = False
    
    def getDataFrame(self) -> pd.DataFrame:
        data = self._data_ref()
        if data is None:
            raise ValueError("DataFrame is deleted.")
        return data
    
    if TYPE_CHECKING:
        def itemDelegate(self) -> TableItemDelegate: ...
        
    def precision(self) -> int:
        return self.itemDelegate().ndigits
    
    def setPrecision(self, ndigits: int) -> None:
        ndigits = int(ndigits)
        if ndigits <= 0:
            raise ValueError("Cannot set negative precision.")
        self.itemDelegate().ndigits = ndigits
        self.refreshTable()
    
    def editability(self) -> bool:
        """Return the editability of the table."""
        return self._editable
    
    def setEditability(self, editable: bool):
        """Set the editability of the table."""
        if editable:
            self.setEditTriggers(_EDITABLE)
        else:
            self.setEditTriggers(_READ_ONLY)
        self._editable = editable
    
    def connectItemChangedSignal(self, slot):
        self.itemChangedSignal.connect(slot)
        return slot
    
    def connectSelectionChangedSignal(self, slot):
        self.selectionChangedSignal.connect(slot)
        return slot
    
    def selectionChanged(self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection) -> None:
        self.selectionChangedSignal.emit(self.getSelections())
        return super().selectionChanged(selected, deselected)
    
    def getSelections(self) -> list[tuple[slice, slice]]:
        """Get list of selections as slicable tuples"""
        selections = self.selectedRanges()
        out: list[tuple[slice, slice]] = []
        for sel in selections:
            r0 = sel.topRow()
            r1 = sel.bottomRow() + 1
            c0 = sel.leftColumn()
            c1 = sel.rightColumn() + 1
            out.append((slice(r0, r1), slice(c0, c1)))
        
        return out

    def setSelections(self, selections: list[tuple[slice, slice]]):
        """Set list of selections."""
        self.clearSelection()
        data = self.getDataFrame()
        nr, nc = data.shape
        try:
            for sel in selections:
                r, c = sel
                r0, r1, _ = r.indices(nr)
                c0, c1, _ = c.indices(nc)
                self.setRangeSelected(
                    QtW.QTableWidgetSelectionRange(r0, c0, r1 - 1, c1 - 1), 
                    True,
                )
        except Exception as e:
            self.clearSelection()
            raise e
        
    def _update_data(self, row: int, col: int):
        item = self.item(row, col)

        r = item.row()
        c = item.column()
        text = item.text()
        
        data = self.getDataFrame()
        dtype = data.dtypes[c]
        try:
            value = _DTYPE_KIND_TO_CONVERTER[dtype.kind](text)
        except Exception as e:
            self.refreshTable()
            updated = False
        else:
            data.iloc[r, c] = value
            updated = True
        return ItemInfo(r, c, value, updated)
        
    
    def verticalScrollbarValueChanged(self, value: int) -> None:
        self.refreshTable()
        return super().verticalScrollbarValueChanged(value)

    def horizontalScrollbarValueChanged(self, value: int) -> None:
        self.refreshTable()
        return super().horizontalScrollbarValueChanged(value)
    
    def rowResized(self, row: int, oldHeight: int, newHeight: int) -> None:
        self.refreshTable()
        return super().rowResized(row, oldHeight, newHeight)
    
    def columnResized(self, column: int, oldWidth: int, newWidth: int) -> None:
        self.refreshTable()
        return super().columnResized(column, oldWidth, newWidth)
    
    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        self.refreshTable()
        return super().resizeEvent(e)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if e.modifiers() & Qt.ControlModifier and e.key() == Qt.Key_C:
            headers = e.modifiers() & Qt.ShiftModifier
            return self.copyToClipboard(headers)
        if e.modifiers() & Qt.ControlModifier and e.key() == Qt.Key_V:
            # TODO
            return 
        
        return super().keyPressEvent(e)
    
    def copyToClipboard(self, headers: bool = True):
        import pandas as pd
        selections = self.getSelections()
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
            show_messagebox(
                mode="error", title="Error", text="Wrong selection range.", parent=self
            )
            return
        else:
            data = self.getDataFrame()
            if nr == 1:
                axis = 1
            else:
                axis = 0
            ref = pd.concat([data.iloc[sel] for sel in selections], axis=axis)
            ref.to_clipboard(index=headers, header=headers)
    
    def refreshTable(self):
        data = self.getDataFrame()
        r0, c0, r1, c1 = self._get_square()
        
        # If DataFrame is partially deleted, table shape should also be updated.
        rmax, cmax = data.shape
        if r1 > rmax:
            for r in range(rmax, r1):
                self.removeRow(rmax)
            r1 = rmax
        if c1 > cmax:
            for c in range(cmax, c1):
                self.removeColumn(cmax)
            c1 = cmax
        
        # If new columns are created, table shape should also be updated
        nrows = self.rowCount()
        ncols = self.columnCount()
        if rmax > nrows:
            for r in range(nrows, rmax):
                self.insertRow(nrows)
        if cmax > ncols:
            for c in range(ncols, cmax):
                self.insertColumn(ncols)
            
        vindex = data.index
        hindex = data.columns
        for r in range(r0, r1):
            vitem = self.verticalHeaderItem(r)
            text = str(vindex[r])
            if vitem is not None:
                vitem.setText(text)
            else:
                self.setVerticalHeaderItem(r, QtW.QTableWidgetItem(text))
            for c in range(c0, c1):
                item = self.item(r, c)
                text = str(data.iloc[r, c])
                if item is not None:
                    self.item(r, c).setText(text)
                else:
                    item = QtW.QTableWidgetItem(text)
                    self.setItem(r, c, item)
                # item.setBackground()
        
        for c in range(c0, c1):
            hitem = self.horizontalHeaderItem(c)
            text = str(hindex[c])
            if hitem is not None:
                hitem.setText(text)
            else:
                self.setHorizontalHeaderItem(c, QtW.QTableWidgetItem(text))
    
    def _get_square(self) -> tuple[int, int, int, int]:
        """Get index range of (row_start, column_start, row_end, column_end)."""
        r0 = self.rowAt(0)
        c0 = self.columnAt(0)
        r1 = self.rowAt(self.height())
        c1 = self.columnAt(self.width())
        if r1 < 0:
            r1 = self.rowCount() - 1
        if c1 < 0:
            c1 = self.columnCount() - 1
        return r0, c0, r1 + 1, c1 + 1

        
        
    def addFilter(self, f):
        # TODO
        ...
    
    # def addFinder(self, finder: Callable[]):
    #     self.findItems()


# modified from magicgui
class TableItemDelegate(QtW.QStyledItemDelegate):
    """Displays table widget items with properly formatted numbers."""
    
    edited = Signal(tuple)
    
    def __init__(self, parent: QtCore.QObject | None = None, ndigits: int = 4) -> None:
        super().__init__(parent)
        self.ndigits = ndigits

    def displayText(self, value, locale):
        return super().displayText(self._format_number(value), locale)

    def setEditorData(self, editor: QtW.QLineEdit, index: QtCore.QModelIndex) -> None:
        super().setEditorData(editor, index)
        # NOTE: This method is evoked when editing started and editing finished.
        # The editor widget has focus only when editing is finished.
        if editor.hasFocus():
            self.edited.emit((index.row(), index.column()))
    
    def paint(self, painter: QtGui.QPainter, option, index: QtCore.QModelIndex) -> None:
        return super().paint(painter, option, index)
        
    def _format_number(self, text: str) -> str:
        """convert string to int or float if possible"""
        try:
            value: int | float | None = int(text)
        except ValueError:
            try:
                value = float(text)
            except ValueError:
                value = None
        
        ndigits = self.ndigits
        
        if isinstance(value, (int, float)):
            if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
                text = str(value) if isinstance(value, int) else f"{value:.{ndigits}f}"
            else:
                text = f"{value:.{ndigits-1}e}"

        return text

_DTYPE_KIND_TO_CONVERTER = {
    "i": int,
    "f": float,
    "u": int,
    "U": str,
    "O": str,
    "c": complex,
}
