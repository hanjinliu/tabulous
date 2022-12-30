from __future__ import annotations
from pathlib import Path

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt, Signal

from tabulous import commands as cmds
from tabulous._qt._toolbar._toolbutton import QColoredToolButton

if TYPE_CHECKING:
    from tabulous.widgets import TableBase

ICON_DIR = Path(__file__).parent / "_icons"


class QHeaderSectionButton(QColoredToolButton):
    def __init__(self, parent: QtW.QWidget = None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        eff = QtW.QGraphicsOpacityEffect()
        eff.setOpacity(0.3)
        self.setGraphicsEffect(eff)
        self._effect = eff

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self._effect.setOpacity(1.0)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._effect.setOpacity(0.3)


class QHeaderSortButton(QHeaderSectionButton):
    sortSignal = Signal(bool)

    def __init__(self, parent: QtW.QWidget = None):
        super().__init__(parent)

        self.setIcon(ICON_DIR / "sort_table.svg")
        self._ascending = True
        self.clicked.connect(self._toggle)

    def _toggle(self):
        if self._ascending:
            self._ascending = False
        else:
            self._ascending = True
        self.sortSignal.emit(self._ascending)

    def ascending(self) -> bool:
        return self._ascending

    @classmethod
    def from_table(cls, table: TableBase, indices: list[int]):
        by = [table.columns[index] for index in indices]

        def _sort(ascending: bool):
            table.proxy.sort(by=by, ascending=ascending)

        for index in indices:
            btn = cls()
            btn.sortSignal.connect(_sort)
            table.native.setHorizontalHeaderWidget(index, btn)

        _sort(True)
        return btn


class QHeaderFilterButton(QHeaderSectionButton):
    def __init__(self, parent: QtW.QWidget = None):
        super().__init__(parent)
        self.setPopupMode(QtW.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setText("▽")

    @classmethod
    def from_table(cls, table: TableBase):
        self = cls()
        qmenu = QtW.QMenu(self)
        qmenu.addAction("Filter by ...", lambda: cmds.table.reset_proxy)
        qmenu.addAction(
            "Reset filter", table._wrap_command(self, cmds.table.reset_proxy)
        )

        return self
