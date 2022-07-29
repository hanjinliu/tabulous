from __future__ import annotations
from typing import Sequence

from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

from ._callback import BoundCallback
from ._keymap import QtKeys, QtKeyMap


class QtKeyMapView(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keymaps")

        area = QtW.QScrollArea()
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        area.setContentsMargins(2, 2, 2, 2)
        area.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setLayout(QtW.QVBoxLayout())
        self.layout().addWidget(area)

        central_widget = QtW.QWidget(area)
        central_widget.setMinimumSize(500, 500)

        _layout = QtW.QVBoxLayout()
        _layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        central_widget.setLayout(_layout)

        area.setWidget(central_widget)

        self._layout = _layout
        self._central_widget = central_widget

    @classmethod
    def from_keymap(cls, kmap: QtKeyMap) -> QtKeyMapView:
        self = cls()
        self.loadKeyMap(kmap)
        return self

    def loadKeyMap(self, kmap: QtKeyMap, offset: tuple[QtKeys, ...] = ()):
        for key, child in kmap.items():
            current_keys = offset + (key,)
            if isinstance(child, QtKeyMap):
                if (c := child.activated_callback) is not None:
                    self.addItem(current_keys, c)
                self.loadKeyMap(child, current_keys)
            else:
                self.addItem(current_keys, child)
        return None

    def addItem(self, keys: Sequence[QtKeys], callback: BoundCallback) -> None:
        item = QtKeyBindItem(key=keys, desc=callback.desc)
        self._layout.addWidget(item)
        return None


class QtKeyBindItem(QtW.QGroupBox):
    def __init__(self, parent=None, key=None, desc=None):
        super().__init__(parent)

        _layout = QtW.QHBoxLayout()
        _layout.setContentsMargins(6, 2, 6, 2)
        self.setLayout(_layout)
        self._key_label = QtW.QLabel()
        self._key_label.setFixedWidth(240)
        self.setFixedHeight(30)
        self._desc = QtW.QLabel()
        _layout.addWidget(self._key_label)
        _layout.addWidget(self._desc)

        if key is not None:
            self.setKeyText(key)
        if desc is not None:
            self.setDescription(desc)

    def setKeyText(self, key: QtKeys | Sequence[QtKeys]) -> None:
        if isinstance(key, QtKeys):
            text = f"<code>{key}</code>"
        else:
            text = " &rarr; ".join(f"<code>{k}</code>" for k in key)
        self._key_label.setText(text)
        return None

    def setDescription(self, desc: str) -> None:
        return self._desc.setText(desc)
