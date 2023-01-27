from __future__ import annotations
from typing import Sequence, TYPE_CHECKING

from qtpy import QtWidgets as QtW
from qtpy.QtCore import Signal

from ._callback import BoundCallback
from ._keymap_objects import QtKeys, QtKeyMap


class QtKeyMapView(QtW.QWidget):
    """A viewer widget for keymap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keymaps")
        _layout = QtW.QVBoxLayout(self)
        self._list = QKeyMapList()
        self._keyseq_edit = QKeyComboEdit()
        _layout.addWidget(self._list)
        _layout.addWidget(self._keyseq_edit)
        self._keyseq_edit.seqChanged.connect(self._list.filter)

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
                self._list.addKeyMapItem(list(current_keys), child)
        return None


class QKeySequenceEdit(QtW.QKeySequenceEdit):
    def timerEvent(self, a0) -> None:
        return None

    def keyCombo(self) -> list[QtKeys]:
        seq = self.keySequence()
        return [QtKeys(s) for s in seq.toString().split(", ") if s]


class QKeyComboEdit(QtW.QWidget):
    seqChanged = Signal(list)

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        _layout = QtW.QHBoxLayout(self)
        _layout.setContentsMargins(0, 0, 0, 0)

        label = QtW.QLabel("Filter: ")
        seq = QKeySequenceEdit()
        apply_btn = QtW.QPushButton("Apply")
        clear_btn = QtW.QPushButton("Clear")

        _layout.addWidget(label)
        _layout.addWidget(seq)
        _layout.addWidget(apply_btn)
        _layout.addWidget(clear_btn)

        self.setLayout(_layout)

        apply_btn.clicked.connect(self.emitKeySequence)
        clear_btn.clicked.connect(self.clear)

        self._keyseq_edit = seq

    def emitKeySequence(self):
        return self.seqChanged.emit(self._keyseq_edit.keyCombo())

    def clear(self):
        self._keyseq_edit.clear()
        self.emitKeySequence()


# ##############################################################################
#    List widget of all the keycombos
# ##############################################################################


class QKeyMapList(QtW.QListWidget):
    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.NoSelection)

    def addKeyMapItem(self, keys: list[QtKeys], callback: BoundCallback):
        item = QtW.QListWidgetItem()
        self.addItem(item)
        self.setItemWidget(item, QtKeyBindItem(key=keys, desc=callback.desc))
        return None

    def filter(self, keys: QtKeys | list[QtKeys]):
        if isinstance(keys, QtKeys):
            keys = [keys]
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            item.setHidden(not widget.startswith(keys))
        return None

    if TYPE_CHECKING:

        def itemWidget(self, item: QtW.QListWidgetItem) -> QtKeyBindItem:
            ...


class QtKeyBindItem(QtW.QWidget):
    """Item widget for QKeyMapList."""

    def __init__(
        self, parent=None, key: QtKeys | Sequence[QtKeys] | None = None, desc: str = ""
    ):
        super().__init__(parent)
        _layout = QtW.QHBoxLayout()
        _layout.setContentsMargins(2, 0, 2, 0)
        self.setLayout(_layout)
        self._key_label = QtW.QLabel()
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

    def startswith(self, prefix: list[QtKeys]) -> bool:
        """True if the key sequence starts with the given prefix."""
        nkey_pref = len(prefix)
        if nkey_pref == 0:
            return True
        elif isinstance(self.key, QtKeys):
            return nkey_pref == 1 and self.key == prefix[0]
        else:
            nkey = len(self.key)
            return nkey_pref <= nkey and prefix == self.key[:nkey_pref]
