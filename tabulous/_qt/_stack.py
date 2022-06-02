from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from ._table import QTableLayer


class QTableStack(QtW.QStackedWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(600, 400)
    
    