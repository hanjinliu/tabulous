from __future__ import annotations
from typing import TYPE_CHECKING

from qtpy import QtWidgets as QtW

if TYPE_CHECKING:
    from ._overlay import QOverlayFrame

# TODO:
class QObjectHolder(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget = None):
        super().__init__(parent)
        _layout = QtW.QVBoxLayout()
        self.setLayout(_layout)

        from tabulous._qt import QTableLayer
        import pandas as pd

        qtable = QTableLayer(
            data=pd.DataFrame([[""]] * 12, columns=["Object"], dtype=object)
        )
        qtable.setTextFormatter("Object", lambda x: repr(x))

        _layout.addWidget(qtable)

    def overlayWidget(self) -> QOverlayFrame:
        return self.parent()

    def parentTable(self):
        return self.overlayWidget().parentTable()

    def parentTableView(self):
        return self.parentTable()._qtable_view

    def close_widget(self):
        qtable = self.parentTableView()
        qtable._selection_model.moved.disconnect(self._on_selection_changed)
        self.hide()
        del qtable._focused_widget
        self.deleteLater()
        qtable.setFocus()
        return None

    def _on_selection_changed(self):
        ...
