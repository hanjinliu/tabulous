from __future__ import annotations
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal

from ..._utils import load_file_open_path


class QStartupWidget(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(12, 12, 12, 12)
        _layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(_layout)
        self._open_file_btn = QClickableLabel("Open Files (Ctrl+O)")
        self._open_new_btn = QClickableLabel("New Spreasheet (Ctrl+N)")
        self._path_list = QPathList()
        _layout.addWidget(self._open_file_btn)
        _layout.addWidget(self._open_new_btn)
        _layout.addWidget(self._path_list)
        self.setMinimumSize(0, 0)
        return None

    def widget(self, i):
        return self

    # def sizeHint(self) -> QtCore.QSize:
    #     return QtCore.QSize(0, 0)


class QClickableLabel(QtW.QLabel):
    """A label widget that behaves like a button."""

    clicked = Signal()

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFont(QtGui.QFont("Arial", 9))
        self.setFixedHeight(32)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Expanding
        )
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        return None

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        return super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        if self.underMouse():
            self.clicked.emit()
        return super().mouseReleaseEvent(ev)

    def enterEvent(self, a0: QtCore.QEvent) -> None:
        font = self.font()
        font.setUnderline(True)
        self.setFont(font)
        return super().enterEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        font = self.font()
        font.setUnderline(False)
        self.setFont(font)
        return super().leaveEvent(a0)


class QPathList(QtW.QGroupBox):
    pathClicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Recent")
        self._layout = QtW.QVBoxLayout()
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(self._layout)
        paths = load_file_open_path()
        for path in paths:
            if path == "":
                continue
            btn = QClickableLabel(path)
            btn.clicked.connect(lambda path=path: self.pathClicked.emit(path))
            self._layout.addWidget(btn)
        return None
