from __future__ import annotations
from typing import TYPE_CHECKING
import weakref
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal
from ._table import QTableLayer

if TYPE_CHECKING:
    from qtpy.QtCore import pyqtBoundSignal

class QTabList(QtW.QListWidget):
    selectionChangedSignal = Signal(int)
    itemMoved = Signal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_src = -1
        self._drag_dst = -1
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtW.QAbstractItemView.DragDropMode.InternalMove)
        self.setMinimumWidth(150)
    
    def addTable(self, table: QTableLayer, name: str = "None"):
        item = QTabListItem(table, parent=self)
        self.addItem(item)
        tab = QTab(parent=self, text=name, table=table)
        item.setSizeHint(tab.sizeHint())
        self.setItemWidget(item, tab)
        return tab
        
    def takeTable(self, index: int) -> QTableLayer:
        item = self.takeItem(index)
        qtab = self.itemWidget(item)
        return qtab.table
    
    def renameTable(self, index: int, name: str):
        item = self.item(index)
        tab = self.itemWidget(item)
        tab.setText(name)
        return None

    def moveTable(self, src: int, dst: int) -> None:
        self.insertItem(dst, self.takeItem(src))
    
    def tableIndex(self, table: QTableLayer) -> int:
        # self.indexFromItem
        for i in range(self.count()):
            if table is self.tableAtIndex(i):
                return i
        else:
            raise ValueError("Table not found.")
    
    def tableAtIndex(self, i: int) -> QTableLayer:
        item = self.item(i)
        qtab = self.itemWidget(item)
        return qtab.table
    
    if TYPE_CHECKING:
        def itemWidget(self, item: QtW.QListWidgetItem) -> QTab: ...
    
    def selectionChanged(
        self,
        selected: QtCore.QItemSelection,
        deselected: QtCore.QItemSelection,
    ) -> None:
        ind = selected.indexes()
        if len(ind) > 0:
            index = ind[0].row()
            self.selectionChangedSignal.emit(index)
            item = self.item(index)
            widget = self.itemWidget(item)
            widget.setHighlight(True)

        for i in deselected.indexes():
            item = self.item(i.row())
            widget = self.itemWidget(item)
            widget.setHighlight(False)
        return super().selectionChanged(selected, deselected)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        self._drag_src = self.indexAt(e.pos()).row()
        self._moving_item = self.item(self._drag_src)
        return super().mousePressEvent(e)
    
    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        if event.keyboardModifiers():
            event.ignore()
        else:
            return super().dragMoveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent):
        if event.keyboardModifiers():
            event.ignore()
            return
    
        widget = self.itemWidget(self.currentItem())
        
        # It seems that QListView has a bug in drag-and-drop.
        # When we tried to move the first item to the upper half region of the
        # second item, the inner widget of the first item dissapears.
        # This bug seemed to be solved to set the inner widget again.
    
        self._drag_dst = self.indexAt(event.pos()).row()
        if self._drag_dst < 0:
            self._drag_dst += self.count()
        if self._drag_src >= 0 and self._drag_src != self._drag_dst:
            super().dropEvent(event)
            item = self.item(self._drag_dst)
            if self.itemWidget(item) is None:
                self.setItemWidget(item, widget)
            self._drag_dst = self.currentIndex()
            if self._drag_src != self._drag_dst:
                self.itemMoved.emit(self._drag_src, self._drag_dst)
            self._drag_src = self._drag_dst = -1
            # self.selectionChangedSignal.emit(self.currentIndex())
            # self.selectedItems()
                
class QTabListItem(QtW.QListWidgetItem):
    def __init__(self, table: QTableLayer, parent=None):
        if not isinstance(table, QTableLayer):
            raise TypeError(f"Cannot add {type(table)}")
        super().__init__(parent=parent)
        self._table_ref = weakref.ref(table)
    
    @property
    def table(self) -> QTableLayer:
        out = self._table_ref()
        if out is None:
            raise ValueError("QTableLayer object is deleted.")
        return out

class QTab(QtW.QFrame):
    def __init__(self, parent=None, text: str = "", table: QTableLayer = None):
        if not isinstance(table, QTableLayer):
            raise TypeError(f"Cannot add {type(table)}")
        
        self._table_ref = weakref.ref(table)
        super().__init__(parent=parent)
        self.setFrameStyle(QtW.QFrame.Shape.StyledPanel)
        self.setLineWidth(1)
        _layout = QtW.QHBoxLayout(self)
        _layout.setContentsMargins(3, 3, 3, 3)
        self._label = _QTabLabel(self, text=text)
        self._close_btn = _QHoverPushButton("x", parent=self)
        
        _layout.addWidget(self._label)
        _layout.addWidget(self._close_btn)
        _layout.setAlignment(self._close_btn, Qt.AlignmentFlag.AlignRight)
        self.setLayout(_layout)
        self.setText(text)
    
    @property
    def table(self) -> QTableLayer:
        out = self._table_ref()
        if out is None:
            raise ValueError("QTableLayer object is deleted.")
        return out
    
    def setText(self, text: str) -> None:
        """Set label text."""
        return self._label.setText(text)
    
    def setHighlight(self, value: bool):
        """Set highlight state of the tab."""
        if value:
            self.setFrameStyle(QtW.QFrame.Shadow.Sunken)
            self.setLineWidth(2)
        else:
            self.setFrameStyle(QtW.QFrame.Shadow.Raised)
            self.setLineWidth(1)

    @property
    def renamed(self) -> pyqtBoundSignal:
        """The child renamed signal."""
        return self._label.renamed
    
    @property
    def buttonClicked(self) -> pyqtBoundSignal:
        """The child button-clicked signal."""
        return self._close_btn.clicked

class _QHoverPushButton(QtW.QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("border: none;")
        self.setFixedWidth(40)
        self.effect = QtW.QGraphicsOpacityEffect(self)
        self.effect.setOpacity(0.0)
        self.setGraphicsEffect(self.effect)
        self.setAutoFillBackground(True)
    
    def enterEvent(self, a0: QtCore.QEvent) -> None:
        self.effect.setOpacity(0.8)
        return super().enterEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        self.effect.setOpacity(0.0)
        return super().leaveEvent(a0)

    
class _QTabLabel(QtW.QLabel):
    renamed = Signal(str)
    
    def __init__(self, parent=None, text: str = ""):
        super().__init__(parent=parent)
        self.setMinimumWidth(120)
        self.setText(text)
    
    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.enterEditingMode()
        return super().mouseDoubleClickEvent(a0)
    
    def enterEditingMode(self):
        line = QtW.QLineEdit(parent=self)

        # set geometry
        edit_geometry = line.geometry()
        edit_geometry.setWidth(self.width())
        edit_geometry.setHeight(self.height())
        edit_geometry.moveTo(self.rect().topLeft())
        line.setGeometry(edit_geometry)
        
        line.setText(self.text())
        line.setHidden(False)
        line.setFocus()
        line.selectAll()
        
        self._line = line # we have to retain the pointer, otherwise got error sometimes
        
        @self._line.editingFinished.connect
        def _():
            self._line.setHidden(True)
            self.renamed.emit(self._line.text())
        return None