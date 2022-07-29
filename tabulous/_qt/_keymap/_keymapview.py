from __future__ import annotations
from typing import Sequence

from qtpy import QtGui, QtWidgets as QtW
from qtpy.QtCore import Qt

from ._callback import BoundCallback
from ._keymap import QtKeys, QtKeyMap


class QtKeyMapView(QtW.QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        _layout = QtW.QVBoxLayout()
        self.setLayout(_layout)
        _layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setMinimumHeight(30)

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
        item = QtKeyBindItem(parent=self, key=keys, desc=callback.desc)
        self.layout().addWidget(item)
        return None


class QtKeyBindItem(QtW.QGroupBox):
    def __init__(self, parent=None, key=None, desc=None):
        super().__init__(parent)

        _layout = QtW.QHBoxLayout()
        self.setLayout(_layout)
        self._key_label = QtW.QLabel()
        self._key_label.setFixedWidth(88)
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
            text = ", ".join(f"<code>{key}</code>" for k in key)
        self._key_label.setText(text)
        return None

    def setDescription(self, desc: str) -> None:
        return self._desc.setText(desc)
