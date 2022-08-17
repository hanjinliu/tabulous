from __future__ import annotations
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Callable
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal

from ..._utils import load_file_open_path

if TYPE_CHECKING:
    from .._mainwindow._base import _QtMainWidgetBase

_HEIGHT = 24


class QStartupWidget(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(12, 12, 12, 12)
        _layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(_layout)

        self._open_table_btn = QClickableLabel("Open File as Table (Ctrl+O)")
        self._open_spreadsheet_btn = QClickableLabel(
            "Open File as Spreadsheet (Ctrl+K, Ctrl+O)"
        )
        self._open_new_btn = QClickableLabel("New Spreadsheet (Ctrl+N)")
        self._path_list = QPathList()

        self._open_table_btn.clicked.connect(lambda: self.mainWidget().openFromDialog())
        self._open_new_btn.clicked.connect(lambda: self.mainWidget().newSpreadSheet())
        self._path_list.pathClicked.connect(
            lambda path: self.mainWidget()._table_viewer.open(path)
        )

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


class QClickableLabel(QtW.QLabel):
    """A label widget that behaves like a button."""

    clicked = Signal()

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setFont(QtGui.QFont("Arial", 9))
        self.setFixedHeight(_HEIGHT)

        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Expanding
        )
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setStyleSheet("QClickableLabel { color: #319DFF; }")
        self.setText(text)
        self._tooltip_func = lambda: ""
        self.setToolTipDuration(200)
        return None

    def setText(self, text: str):
        fm = QtGui.QFontMetrics(self.font())
        width = fm.width(text)
        self.setFixedWidth(width)
        return super().setText(text)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        return super().mouseReleaseEvent(ev)

    def enterEvent(self, a0: QtCore.QEvent) -> None:
        font = self.font()
        font.setUnderline(True)
        self.setFont(font)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()
        return super().enterEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        font = self.font()
        font.setUnderline(False)
        self.setFont(font)
        self.unsetCursor()
        return super().leaveEvent(a0)

    def setTooltipFunction(self, f: Callable[[], str]) -> None:
        self._tooltip_func = f
        return None

    def event(self, event: QtCore.QEvent):
        if event.type() == QtCore.QEvent.Type.ToolTip:
            tooltip = self._tooltip_func()
            QtW.QToolTip.showText(QtGui.QCursor.pos(), tooltip, self)
            return True
        else:
            return super().event(event)


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
            btn.setTooltipFunction(lambda path=path: self.previewString(path))
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

    def previewString(self, path: str) -> str:
        """Preview the path."""
        _path = Path(path)
        if not _path.exists():
            return "Path does not exist"

        suf = _path.suffix
        import pandas as pd

        if suf in (".csv", ".txt", ".dat"):
            reader = pd.read_csv

        elif suf in (".xlsx", ".xls", ".xlsb", ".xlsm", ".xltm", "xltx", ".xml"):
            reader = partial(pd.read_excel, sheet_name=0)

        else:
            return "Preview not available."

        try:
            columns = reader(path, nrows=0).columns.tolist()
            if len(columns) > 5:
                columns = columns[:5]
                large_col = True
            else:
                large_col = False

            df = reader(path, nrows=12, usecols=columns)
            if large_col:
                df[" ... "] = [" ... "] * len(df)

        except Exception:
            return "Preview not available."

        out = df.to_html(float_format="%.4g")
        if len(df) == 12:
            s0, s1 = out.rsplit("</tr>", maxsplit=1)
            foot = "<td align='center'>:</td>" * df.shape[1]
            out = f"{s0}</tr><tr><th align='center'>:</th>{foot}</tr>{s1}"

        return out
