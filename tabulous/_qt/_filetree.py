from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtWidgets import QFileSystemModel
from qtpy.QtCore import Qt

from magicgui.widgets import FileEdit

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase


class QFileTreeWidget(QtW.QTreeView):
    """A file tree widget for tabulous"""

    def __init__(self, parent: QtW.QWidget = None):
        super().__init__(parent)
        self.setRootIsDecorated(True)
        self.setAnimated(True)
        self.setIndentation(20)
        self.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.setDropIndicatorShown(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.setUniformRowHeights(True)
        self.setAlternatingRowColors(False)
        self.setExpandsOnDoubleClick(True)
        self.setModel(QFileSystemModel())
        for i in range(1, self.model().columnCount()):
            self.hideColumn(i)
        self.doubleClicked.connect(self._open_at_index)

    def model(self) -> QFileSystemModel:
        return super().model()

    def setRoot(self, path: str):
        path = str(path)
        index = self.model().setRootPath(path)
        self.setHeaderHidden(True)
        self.setRootIndex(index)

    def _on_context_menu(self, point: QtCore.QPoint):
        menu = QtW.QMenu(self)
        index = self.indexAt(point)
        menu.addAction(
            "Open as table", lambda: self._open_at_index(index, type="table")
        )
        menu.addAction(
            "Open as spreadsheet",
            lambda: self._open_at_index(index, type="spreadsheet"),
        )
        menu.exec_(self.viewport().mapToGlobal(point))

    def _find_viewer(self) -> TableViewerBase | None:
        parent = self.parentWidget()
        while parent is not None:
            parent = parent.parentWidget()
            if hasattr(parent, "_table_viewer"):
                return parent._table_viewer
        return None

    def _open_at_index(self, index: QtCore.QModelIndex, type: str = "table"):
        path = self.model().filePath(index)
        if not self.model().isDir(index):
            if viewer := self._find_viewer():
                path = self.model().filePath(index)
                viewer.open(path, type=type)


class QFileExplorer(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget = None):
        super().__init__(parent)
        self._layout = QtW.QVBoxLayout(self)
        self._file_edit = FileEdit(mode="d")
        self._file_edit.line_edit.tooltip = "Root directory"
        self._file_edit.choose_btn.text = "..."
        self._file_tree = QFileTreeWidget(self)
        curpath = QtCore.QDir.currentPath()
        self._file_tree.setRoot(curpath)
        self._file_edit.value = Path(curpath)
        self._layout.addWidget(self._file_edit.native)
        self._layout.addWidget(self._file_tree)
        self._file_edit.changed.connect(self._update_root)
        self._update_root(curpath)

    def _update_root(self, path: str):
        if Path(path).exists():
            self._file_tree.setRoot(str(path))
