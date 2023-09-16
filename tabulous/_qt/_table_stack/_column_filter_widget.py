from __future__ import annotations
from enum import Enum

from qtpy import QtCore, QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt, Signal
from tabulous._sort_filter_proxy import ColumnFilter

from superqt import QEnumComboBox


class ColumnFilterType(Enum):
    none = "Select ..."
    startswith = "starts with"
    endswith = "ends with"
    contains = "contains"
    isin = "is in"
    regex = "matches"


class QColumnFilterWidget(QtW.QWidget):
    """A widget for filtering a column of a table."""

    requireResize = Signal(QtCore.QSize)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(150)
        self._cbox = QEnumComboBox(enum_class=ColumnFilterType)
        self._cbox.setMinimumWidth(100)
        self._cbox.setFont(QtGui.QFont("Arial", 10))
        self._string_edit = QtW.QLineEdit()
        self._string_edit.setFixedWidth(84)
        self._call_button = QtW.QPushButton("Apply")
        self._call_button.setToolTip("Apply column filter")
        self._reset_button = QtW.QPushButton("Reset")
        self._reset_button.setToolTip("Reset column filter")
        self._setup_ui()

        self._cbox.currentEnumChanged.connect(self._type_changed)
        self._call_button.clicked.connect(self._call_button_clicked)
        self._reset_button.clicked.connect(self._reset)
        self._type_changed(ColumnFilterType.none)

    def _type_changed(self, val: ColumnFilterType):
        pass

    def _current_table(self):
        from . import QTabbedTableStack

        ins = self.parent()
        while ins is not None:
            if isinstance(ins, QTabbedTableStack):
                idx = ins.currentIndex()
                qtable = ins.tableAtIndex(idx)
                return qtable
            ins = ins.parent()
        return None

    def _call_button_clicked(self):
        qtable = self._current_table()
        if qtable is None:
            return
        qtable.setColumnFilter(self.get_filter())

    def _reset(self):
        qtable = self._current_table()
        if qtable is None:
            return
        qtable.setColumnFilter(ColumnFilter.identity())

    def get_filter(self) -> ColumnFilter:
        ftype: ColumnFilterType = self._cbox.currentEnum()
        arg = self._string_edit.text()
        if ftype is ColumnFilterType.none:
            return ColumnFilter.identity()
        elif ftype is ColumnFilterType.startswith:
            return ColumnFilter.startswith(arg)
        elif ftype is ColumnFilterType.endswith:
            return ColumnFilter.endswith(arg)
        elif ftype is ColumnFilterType.contains:
            return ColumnFilter.contains(arg)
        elif ftype is ColumnFilterType.isin:
            return ColumnFilter.isin(arg)
        elif ftype is ColumnFilterType.regex:
            return ColumnFilter.regex(arg)
        else:
            raise RuntimeError(f"Unknown filter type: {ftype}")

    def _setup_ui(self):
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(2, 2, 2, 2)

        _layout.addWidget(QtW.QLabel("Filter by:"))

        _middle = QtW.QWidget()
        _middle_layout = QtW.QHBoxLayout()
        _middle_layout.setContentsMargins(0, 0, 0, 0)
        _middle_layout.addWidget(self._cbox, alignment=Qt.AlignmentFlag.AlignLeft)
        _middle_layout.addWidget(
            self._string_edit, alignment=Qt.AlignmentFlag.AlignRight
        )
        _middle.setLayout(_middle_layout)

        _layout.addWidget(_middle)

        _bottom = QtW.QWidget()
        _bottom_layout = QtW.QHBoxLayout()
        _bottom_layout.setContentsMargins(0, 0, 0, 0)
        _bottom_layout.addWidget(self._call_button)
        _bottom_layout.addWidget(self._reset_button)
        _bottom.setLayout(_bottom_layout)
        _layout.addWidget(_bottom)
        self.setLayout(_layout)
