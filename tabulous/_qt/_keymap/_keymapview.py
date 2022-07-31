from __future__ import annotations
from typing import Sequence, TYPE_CHECKING

from qtpy import QtWidgets as QtW, QtGui

from ._callback import BoundCallback
from ._keymap import QtKeys, QtKeyMap


class QtKeyMapView(QtW.QWidget):
    """A viewer widget for keymap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keymaps")
        _layout = QtW.QVBoxLayout(self)
        self._list = QKeyMapList()
        # self._keyseq_edit = QtW.QKeySequenceEdit()
        _layout.addWidget(self._list)
        # _layout.addWidget(self._keyseq_edit)

        self.setLayout(_layout)
        self._layout = _layout
        self.setMinimumWidth(520)

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
                    self._list.addKeyMapItem(current_keys, c)
                self.loadKeyMap(child, current_keys)
            else:
                self._list.addKeyMapItem(current_keys, child)
        return None


class QKeyMapList(QtW.QListWidget):
    def addKeyMapItem(self, keys: Sequence[QtKeys], callback: BoundCallback):
        item = QtW.QListWidgetItem()
        self.addItem(item)
        self.setItemWidget(item, QtKeyBindItem(key=keys, desc=callback.desc))
        return None

    # def filter(self, string: str):
    #     # TODO
    #     keys = QtKeys(string)
    #     for i in self.count():
    #         item = self.item(i)
    #         widget = self.itemWidget(item)
    #         widget.key.key | widget.key.modifier
    #         item.setHidden(False)

    if TYPE_CHECKING:

        def itemWidget(self, item: QtW.QListWidgetItem) -> QtKeyBindItem:
            ...


class QtKeyBindItem(QtW.QGroupBox):
    def __init__(
        self, parent=None, key: QtKeys | Sequence[QtKeys] | None = None, desc: str = ""
    ):
        super().__init__(parent)
        _layout = QtW.QHBoxLayout()
        _layout.setContentsMargins(2, 0, 2, 0)
        self.setLayout(_layout)
        self._key_label = QtW.QLabel()
        self._key_label.setFixedWidth(240)
        self._desc = QtW.QLabel()
        _layout.addWidget(self._key_label)
        _layout.addWidget(self._desc)

        self.setKeyText(key)
        self.setDescription(desc)
        self.key = key

    def setKeyText(self, key: QtKeys | Sequence[QtKeys]) -> None:
        if isinstance(key, QtKeys):
            text = f"<code>{key}</code>"
        else:
            text = " &rarr; ".join(f"<code>{k}</code>" for k in key)
        self._key_label.setText(text)
        return None

    def setDescription(self, desc: str) -> None:
        return self._desc.setText(desc)
