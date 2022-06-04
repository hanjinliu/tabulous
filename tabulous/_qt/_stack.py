from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Signal

class QTableStack(QtW.QStackedWidget):
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
        else:
            return super().dragEnterEvent()