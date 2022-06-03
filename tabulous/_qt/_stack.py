from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from ._table import QTableLayer


class QTableStack(QtW.QStackedWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(600, 400)
    
    def moveWidget(self, src: int, dst: int) -> None:
        """Move (reorder) child widgets"""
        w = self.widget(src)
        self.removeWidget(w)
        self.insertWidget(dst, w)
        
        return None