from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt, Signal
from tabulous._qt._clickable_label import QClickableLabel
from tabulous._utils import load_file_open_path
from tabulous import commands as cmds

if TYPE_CHECKING:
    from .._mainwindow._base import _QtMainWidgetBase

_HEIGHT = 24


class QStartupWidget(QtW.QWidget):
    """The startup widget which is shown when no table exists."""

    def __init__(self, parent=None):
        super().__init__(parent)
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(12, 12, 12, 12)
        _layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(_layout)

        # fmt: off
        self._open_table_btn = QClickableLabel("Open File as Table (Ctrl+O)")
        self._open_spreadsheet_btn = QClickableLabel("Open File as Spreadsheet (Ctrl+K, Ctrl+O)")
        self._open_new_btn = QClickableLabel("New Spreadsheet (Ctrl+N)")
        self._path_list = QPathList()

        self._open_table_btn.clicked.connect(lambda: cmds.file.open_table(self.mainWidget()._table_viewer))
        self._open_spreadsheet_btn.clicked.connect(lambda: cmds.file.open_spreadsheet(self.mainWidget()._table_viewer))
        self._open_new_btn.clicked.connect(lambda: cmds.table.new_spreadsheet(self.mainWidget()._table_viewer))
        self._path_list.pathClicked.connect(lambda path: self.mainWidget()._table_viewer.open(path))
        # fmt: on
        _layout.addWidget(self._open_table_btn)
        _layout.addWidget(self._open_spreadsheet_btn)
        _layout.addWidget(self._open_new_btn)
        _layout.addWidget(self._path_list)
        self.setMinimumSize(0, 0)
        return None

    def mainWidget(self) -> _QtMainWidgetBase:
        """The parent main widget."""
        return self.parent().parent().parent()

    def widget(self, i):
        return self

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        h = a0.size().height()
        rest = max(h - _HEIGHT * 2 - 30, 0)
        n_show = rest // (_HEIGHT + 4)
        self._path_list.setShownCount(n_show)
        return super().resizeEvent(a0)


class QPathList(QtW.QGroupBox):
    pathClicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Recent")
        _layout = QtW.QVBoxLayout()
        _layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(_layout)
        paths = load_file_open_path()
        self._buttons: list[QClickableLabel] = []
        for path in reversed(paths):
            if path == "":
                continue
            btn = QClickableLabel(path)
            btn.clicked.connect(lambda path=path: self.pathClicked.emit(path))
            _layout.addWidget(btn)
            self._buttons.append(btn)
        return None

    def setShownCount(self, n: int):
        """Set how many buttons to be shown."""
        _layout: QtW.QVBoxLayout = self.layout()
        n_wdt = _layout.count()
        if n > n_wdt:
            n = n_wdt

        for i in range(0, n):
            self._buttons[i].show()
        for i in range(n, n_wdt):
            self._buttons[i].hide()
        return None
