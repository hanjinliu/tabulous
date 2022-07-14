from __future__ import annotations
from typing import TYPE_CHECKING
import weakref
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal

from ._base import _QTableStackBase
from ._utils import create_temporal_line_edit

from .._table import QBaseTable

if TYPE_CHECKING:
    from qtpy.QtCore import pyqtBoundSignal

class QListTableStack(QtW.QSplitter, _QTableStackBase):
    currentTableChanged = Signal(int)
    itemDropped = Signal(object)
    itemMoved = Signal(int, int)
    tableRenamed = Signal(int, str)
    tableRemoved = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._tabs = QTabList()
        self._stack = QTableStack()
        self.addWidget(self._tabs)
        self.addWidget(self._stack)
        
        # connect signals
        @self._tabs.currentTableChanged.connect
        def _current_table_changed(index):
            qtable = self.tableAtIndex(index)
            self._stack.setCurrentWidget(qtable)
        
        self._tabs.itemMoved.connect(self._stack.moveWidget)
        self._tabs.itemMoved.connect(self.itemMoved.emit)
        self._stack.dropped.connect(self.itemDropped.emit)
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.installContextMenu()

    
    def addTable(self, table: QBaseTable, name: str = "None") -> None:
        """Add `table` to stack as name `name`."""
        item = QtW.QListWidgetItem(self._tabs)
        self._tabs.addItem(item)
        tab = QTab(parent=self._tabs, text=name, table=table)
        item.setSizeHint(tab.sizeHint())
        self._tabs.setItemWidget(item, tab)
        self._stack.addWidget(table)
        @tab.renamed.connect
        def _tab_renamed(name: str):
            for i in range(self._tabs.count()):
                item = self._tabs.item(i)
                tab0 = self._tabs.itemWidget(item)
                if tab0 is tab:
                    self.tableRenamed.emit(i, name)
                    break
        @tab.buttonClicked.connect
        def _tab_removing():
            index = self.tableIndex(tab.table)
            self.takeTable(index)
            self.tableRemoved.emit(index)
        return None
        
    def takeTable(self, index: int) -> QBaseTable:
        """Remove table at `index` and return it."""
        item = self._tabs.item(index)
        qtab = self._tabs.itemWidget(item)
        self._tabs.takeItem(index)
        for child in self._stack.children():
            if child is qtab.table:
                child.setParent(None)
            
        return qtab.table
    
    def renameTable(self, index: int, name: str):
        """Rename table at `index` to `name`."""
        item = self._tabs.item(index)
        tab = self._tabs.itemWidget(item)
        tab.setText(name)
        return None
    
    def tableIndex(self, table: QBaseTable) -> int:
        """Get the index of `table`."""
        for i in range(self._tabs.count()):
            if table is self.tableAtIndex(i):
                return i
        else:
            raise ValueError("Table not found.")
    
    def tableAtIndex(self, i: int) -> QBaseTable:
        """Get the table at `i`."""
        item = self._tabs.item(i)
        qtab = self._tabs.itemWidget(item)
        return qtab.table
    
    def tableAt(self, pos: QtCore.QPoint) -> QBaseTable:
        """Return table at a mouse position."""
        item = self._tabs.itemAt(pos)
        if item is None:
            return None
        return self._tabs.itemWidget(item).table
    
    def moveTable(self, src: int, dst: int):
        """Move table from `src` to `dst`."""
        self._tabs.moveTable(src, dst)
        self._stack.moveWidget(src, dst)
        self.setCurrentIndex(dst)
        self._stack.setCurrentIndex(dst)
        return None
    
    def currentIndex(self) -> int:
        """Return the current active table index."""
        return self._stack.currentIndex()
    
    def setCurrentIndex(self, i: int):
        """Set the current active table index and update the widget."""
        return self._tabs.setCurrentRow(i)
    
    def enterEditingMode(self, index: int):
        """Enter edit table name mode."""
        item = self._tabs.item(index)
        qtab = self._tabs.itemWidget(item)
        qtab._label.enterEditingMode()
        return None

class QTabList(QtW.QListWidget):
    currentTableChanged = Signal(int)
    itemMoved = Signal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_src: int | None = None
        self._drag_dst: int | None = None
        
        # settings
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(QtW.QAbstractItemView.DragDropMode.InternalMove)
        self.setMinimumWidth(190)
    
    if TYPE_CHECKING:
        def itemWidget(self, item: QtW.QListWidgetItem) -> QTab: ...
    
    def moveTable(self, src: int, dst: int) -> None:
        """Move table from index `src` to `dst`."""
        if src < dst:
            dst += 1
        self.model().moveRow(QtCore.QModelIndex(), src, QtCore.QModelIndex(), dst)

    def selectionChanged(
        self,
        selected: QtCore.QItemSelection,
        deselected: QtCore.QItemSelection,
    ) -> None:
        ind = selected.indexes()
        if len(ind) > 0:
            index = ind[0].row()
            self.currentTableChanged.emit(index)
            item = self.item(index)
            widget = self.itemWidget(item)
            widget.setHighlight(True)

        for i in deselected.indexes():
            item = self.item(i.row())
            widget = self.itemWidget(item)
            if widget is not None:
                widget.setHighlight(False)
        return super().selectionChanged(selected, deselected)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        self._drag_src = self.indexAt(e.pos()).row()
        return super().mousePressEvent(e)
    
    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        if event.keyboardModifiers():
            event.ignore()
        else:
            return super().dragMoveEvent(event)
    
    def dropEvent(self, event: QtGui.QDropEvent):
        if event.keyboardModifiers() or self._drag_src is None:
            event.ignore()
            return
        # It seems that QListView has a bug in drag-and-drop.
        # When we tried to move the first item to the upper half region of the
        # second item, the inner widget of the first item dissapears.
        # This bug seemed to be solved to set the inner widget again.
    
        self._drag_dst = self.indexAt(event.pos()).row()
        if self._drag_dst < 0:
            self._drag_dst += self.count()
        if self._drag_src >= 0 and self._drag_src != self._drag_dst:
            self.moveTable(self._drag_src, self._drag_dst)
            self.setCurrentRow(self._drag_dst)
            if self._drag_src != self._drag_dst:
                self.itemMoved.emit(self._drag_src, self._drag_dst)
            self._drag_src = self._drag_dst = None


class QTab(QtW.QFrame):
    def __init__(self, parent=None, text: str = "", table: QBaseTable = None):
        if not isinstance(table, QBaseTable):
            raise TypeError(f"Cannot add {type(table)}")
        
        self._table_ref = weakref.ref(table)
        super().__init__(parent=parent)
        self.setFrameStyle(QtW.QFrame.Shape.Box)
        self.setLineWidth(1)
        _layout = QtW.QHBoxLayout(self)
        _layout.setContentsMargins(3, 3, 3, 3)
        self._label = _QTabLabel(self, text=text)
        self._close_btn = _QHoverPushButton(parent=self)
        icon = QtW.QApplication.style().standardIcon(QtW.QStyle.StandardPixmap.SP_TitleBarCloseButton)
        self._close_btn.setIcon(icon)
        self._close_btn.setIconSize(QtCore.QSize(16, 16))
        
        _layout.addWidget(self._label)
        _layout.addWidget(self._close_btn)
        _layout.setAlignment(self._close_btn, Qt.AlignmentFlag.AlignRight)
        self.setLayout(_layout)
        self.setText(text)
    
    @property
    def table(self) -> QBaseTable:
        out = self._table_ref()
        if out is None:
            raise ValueError("QTableLayer object is deleted.")
        return out
    
    def text(self) -> str:
        """Get label text."""
        return self._label.text()
    
    def setText(self, text: str) -> None:
        """Set label text."""
        return self._label.setText(text)
    
    def setHighlight(self, value: bool):
        """Set highlight state of the tab."""
        if value:
            font = self._label.font()
            font.setBold(True)
            self._label.setFont(font)
            self.setLineWidth(2)
        else:
            font = self._label.font()
            font.setBold(False)
            self._label.setFont(font)
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
    """A push button widget that disappears when mouse leaves."""
    
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
    
    def keyPressEvent(self, ev: QtGui.QKeyEvent) -> None:
        if ev.key() == Qt.Key.Key_F2:
            return self.enterEditingMode()
        return super().keyPressEvent(ev)
    
    def enterEditingMode(self):
        line = create_temporal_line_edit(self.rect(), self, self.text())
        self._line = line
        
        @self._line.editingFinished.connect
        def _():
            self._line.setHidden(True)
            text = self._line.text()
            self.setText(text)
            self.renamed.emit(text)
        return None

class QTableStack(QtW.QStackedWidget):
    """The stacked widget region."""
    
    dropped = Signal(object)
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setAcceptDrops(True)
    
    def moveWidget(self, src: int, dst: int) -> None:
        """Move (reorder) child widgets"""
        w = self.widget(src)
        self.removeWidget(w)
        self.insertWidget(dst, w)
        
        return None
    
    def dropEvent(self, a0: QtGui.QDropEvent) -> None:
        mime = a0.mimeData()
        self.dropped.emit(mime.text())
        return super().dropEvent(a0)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        if e.mimeData().hasText():
            e.accept()
            return None
        elif isinstance(e.source(), _QTableStackBase):
            e.accept()
            return None
        else:
            return super().dragEnterEvent(e)
