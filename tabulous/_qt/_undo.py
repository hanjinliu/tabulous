from __future__ import annotations
from typing import Any
from collections_undo import UndoManager, fmt
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal

import numpy as np
import pandas as pd

_MONOSPACE = QtGui.QFont("Monospace")
_MONOSPACE.setStyleHint(QtGui.QFont.StyleHint.TypeWriter)


class QUndoStackViewer(QtW.QWidget):
    """A viewer of the undo stack"""

    def __init__(self, mgr: UndoManager):
        super().__init__()
        self._mgr = mgr
        self._listview = QtW.QListView()
        self._listview.setModel(QUndoStackModel(mgr))
        mgr.called.append(self.refresh)

        self._undo_button = QtW.QPushButton("Undo")
        self._redo_button = QtW.QPushButton("Redo")
        self._undo_button.setToolTip("Undo the last action")
        self._redo_button.setToolTip("Redo the last undone action")

        _layout = QtW.QVBoxLayout()
        _layout.addWidget(self._listview)
        self.setLayout(_layout)

        _footer = QtW.QWidget()
        _footer_layout = QtW.QHBoxLayout()
        _footer_layout.setContentsMargins(0, 0, 0, 0)
        _footer_layout.addWidget(self._undo_button)
        _footer_layout.addWidget(self._redo_button)
        _footer.setLayout(_footer_layout)

        _layout.addWidget(_footer)

        self._undo_button.clicked.connect(self._mgr.undo)
        self._redo_button.clicked.connect(self._mgr.redo)
        self.setMinimumHeight(160)

    def refresh(self, *_):
        self._listview.model().updateUndoShape()
        self._listview.viewport().update()


class QUndoStackModel(QtCore.QAbstractListModel):
    def __init__(self, mgr: UndoManager) -> None:
        super().__init__()
        self._mgr = mgr
        self._current_size = 0

    def data(
        self, index: QtCore.QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid():
            return QtCore.QVariant()
        if role == Qt.ItemDataRole.DisplayRole:
            r = index.row()
            stack = self._mgr.stack_undo
            if r < len(stack):
                try:
                    desc = stack[r].format()
                except Exception as e:
                    desc = f"{type(e).__name__}: {e}"
                return desc

        elif role == Qt.ItemDataRole.FontRole:
            return _MONOSPACE

        return QtCore.QVariant()

    def updateUndoShape(self):
        nr = self._mgr.stack_lengths[0]
        nr0 = self._current_size
        if nr0 < nr:
            self.beginInsertRows(QtCore.QModelIndex(), nr0, nr - 1)
            self.insertRows(nr0, nr - nr0, QtCore.QModelIndex())
            self.endInsertRows()
        elif nr < nr0:
            self.beginRemoveRows(QtCore.QModelIndex(), nr, nr0 - 1)
            self.removeRows(nr, nr0 - nr, QtCore.QModelIndex())
            self.endRemoveRows()
        self._current_size = nr

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._mgr.stack_undo)

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


class QtUndoManager(UndoManager):
    def __init__(self, maxsize=1e7) -> None:
        super().__init__(measure=_count_data_size, maxsize=maxsize)
        self._widget = None

    def widget(self) -> QUndoStackViewer:
        if self._widget is None:
            self._widget = QUndoStackViewer(self)
        return self._widget


def _count_data_size(*args, **kwargs) -> float:
    total_nbytes = 0
    for arg in args:
        total_nbytes += _getsizeof(arg)
    for v in kwargs.values():
        total_nbytes += _getsizeof(v)
    return total_nbytes


def _getsizeof(obj) -> float:
    if isinstance(obj, pd.DataFrame):
        nbytes = obj.memory_usage(deep=True).sum()
    elif isinstance(obj, pd.Series):
        nbytes = obj.memory_usage(deep=True)
    elif isinstance(obj, np.ndarray):
        nbytes = obj.nbytes
    elif isinstance(obj, (list, tuple, set)):
        nbytes = sum(_getsizeof(x) for x in obj)
    elif isinstance(obj, dict):
        nbytes = sum(_getsizeof(x) for x in obj.values())
    else:
        nbytes = 1  # approximate
    return nbytes


def fmt_slice(sl: slice) -> str:
    if not isinstance(sl, slice):
        return fmt.map_object(sl)
    return f"{sl.start}:{sl.stop}"
