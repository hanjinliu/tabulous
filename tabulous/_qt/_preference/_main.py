from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt

from ._theme import QThemePanel
from ._table_config import QTableConfigPanel
from ._shared import QTitleLabel

if TYPE_CHECKING:
    from tabulous._qt._mainwindow import _QtMainWidgetBase


class QPreferenceDialog(QtW.QDialog):
    def __init__(self, viewer: _QtMainWidgetBase) -> None:
        super().__init__(viewer)
        self._viewer = viewer
        self.setWindowTitle("Preferences")
        self.resize(600, 400)
        layout = QtW.QHBoxLayout()
        self.setLayout(layout)

        self._list = QtW.QListWidget(self)
        self._list.setFixedWidth(150)
        self._stack = QtW.QStackedWidget(self)

        self._list.itemClicked.connect(
            lambda: self._stack.setCurrentIndex(self._list.currentRow())
        )

        layout.addWidget(self._list)
        layout.addWidget(self._stack)

        self._setup_panels()

    def addPanel(self, name: str):
        self._list.addItem(name)
        widget = QtW.QWidget(self._stack)
        layout = QtW.QVBoxLayout()
        widget.setLayout(layout)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._stack.addWidget(widget)
        return widget

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if (
            a0.key() == Qt.Key.Key_W
            and a0.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.close()
        return super().keyPressEvent(a0)

    def _setup_panels(self):
        panel_general = self.addPanel("General")
        panel_general.layout().addWidget(QtW.QLabel("TODO"))
        panel_apperance = self.addPanel("Apperance")
        panel_apperance.layout().addWidget(QTitleLabel("Theme", 18))
        panel_apperance.layout().addWidget(QThemePanel(self))
        panel_table = self.addPanel("Table")
        panel_table.layout().addWidget(QTitleLabel("Table Configuation", 18))
        panel_table.layout().addWidget(QTableConfigPanel(self))
