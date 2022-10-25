from __future__ import annotations
from typing import TYPE_CHECKING, cast
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt

from ._table_base import QBaseTable
from ._line_edit import QCellLineEdit, QCellLiteralEdit

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd
    from pandas.core.dtypes.dtypes import CategoricalDtype
    from ._enhanced_table import _QTableViewEnhanced
    from ._item_model import AbstractDataFrameModel


class TableItemDelegate(QtW.QStyledItemDelegate):
    """Displays table widget items with properly formatted numbers."""

    def createEditor(
        self, parent: QtW.QWidget, option, index: QtCore.QModelIndex
    ) -> QtW.QWidget:
        """Create different type of editors for different dtypes."""
        qtable_view: _QTableViewEnhanced = parent.parent()
        table: QBaseTable = qtable_view.parentTable()
        if qtable_view.model()._editable:
            model = qtable_view.model()
            df = model.df
            row = index.row()
            col = index.column()
            font = QtGui.QFont(
                qtable_view._font, int(qtable_view._font_size * qtable_view.zoom())
            )
            if row >= df.shape[0] or col >= df.shape[1]:
                # out-of-bounds
                line = QCellLineEdit(parent, table, (row, col))
                line.setFont(font)
                return line

            dtype: np.dtype = df.dtypes.values[col]
            value = df.iat[row, col]
            if dtype == "category":
                # use combobox for categorical data
                dtype: CategoricalDtype
                cbox = QtW.QComboBox(parent)
                cbox.setFont(font)
                choices = list(map(str, dtype.categories))
                cbox.addItems(choices)
                cbox.setCurrentIndex(choices.index(value))
                cbox.currentIndexChanged.connect(qtable_view.setFocus)
                return cbox
            elif dtype == "bool":
                # use checkbox for boolean data
                cbox = QtW.QComboBox(parent)
                cbox.setFont(font)
                choices = ["True", "False"]
                cbox.addItems(choices)
                cbox.setCurrentIndex(0 if value else 1)
                cbox.currentIndexChanged.connect(qtable_view.setFocus)
                return cbox
            elif dtype.kind == "M":
                dt = QtW.QDateTimeEdit(parent)
                dt.setFont(font)
                value: pd.Timestamp
                dt.setDateTime(value.to_pydatetime())
                return dt
            else:
                line = QCellLineEdit(parent, table, (row, col))
                if table._get_ref_expr(row, col):
                    # QCellLiteralEdit has its own font.
                    line.setFocus()
                else:
                    line.setFont(font)
                return line

    def setEditorData(self, editor: QtW.QWidget, index: QtCore.QModelIndex) -> None:
        super().setEditorData(editor, index)
        if isinstance(editor, QtW.QComboBox):
            editor = cast(QtW.QComboBox, editor)
            editor.showPopup()
        return None

    def setModelData(
        self,
        editor: QtW.QWidget,
        model: AbstractDataFrameModel,
        index: QtCore.QModelIndex,
    ) -> None:
        if isinstance(editor, QtW.QDateTimeEdit):
            editor = cast(QtW.QDateTimeEdit, editor)
            dt = editor.dateTime().toPyDateTime()
            model.setData(index, dt, Qt.ItemDataRole.EditRole)
        else:
            return super().setModelData(editor, model, index)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtW.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ):
        option.textElideMode = Qt.TextElideMode.ElideNone
        return super().paint(painter, option, index)

    def initStyleOption(
        self, option: QtW.QStyleOptionViewItem, index: QtCore.QModelIndex
    ):
        super().initStyleOption(option, index)
        if option.state & QtW.QStyle.StateFlag.State_HasFocus:
            option.state = option.state & ~QtW.QStyle.StateFlag.State_HasFocus

    def parentTable(self) -> QBaseTable:
        return self.parent().parent()


# TODO: add timedelta-specific editor

# class QTimeRangeEdit(QtW.QAbstractSpinBox):
#     def __init__(self, val: pd.Timedelta, parent: QtW.QWidget | None = None) -> None:
#         super().__init__(parent)
#         self._value = val
#         self.setLineEdit

#     def text(self):
#         return str(self._value)

#     def setValue(self, val: pd.Timedelta):
#         self._value = str(val)

# class QTimerangeLineEdit(QtW.QLineEdit):
#     def __init__(self, val: pd.Timedelta, parent: QtW.QWidget | None = None) -> None:
#         super().__init__(parent)
#         self._value = val
#         self.setText(str(val))
