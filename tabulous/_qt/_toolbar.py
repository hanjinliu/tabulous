from __future__ import annotations
from typing import TYPE_CHECKING, Callable, TypeVar
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtWidgets import QAction
from qtpy.QtCore import Qt, QEvent

if TYPE_CHECKING:
    from ._mainwindow import _QtMainWidgetBase
    from ..widgets.mainwindow import _TableViewerBase

class QTableStackToolBar(QtW.QToolBar):
    def __init__(self, parent: _QtMainWidgetBase):
        super().__init__(parent)
        self.addAction()
    
    @property
    def viewer(self) -> _TableViewerBase:
        return self.parent()._table_viewer

    if TYPE_CHECKING:
        def parent(self) -> _QtMainWidgetBase:
            ...
    
    def open_file(self):
        path = QtW.QFileDialog.getOpenFileName(self.parent(), "Open File", "", "CSV Files (*.csv)")
        if path:
            self.viewer.open(path)