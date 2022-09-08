from __future__ import annotations
from typing import TYPE_CHECKING, cast
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt

from ._table_base import QBaseTable
from ._line_edit import QCellLineEdit

if TYPE_CHECKING:
    import numpy as np
    from pandas.core.dtypes.dtypes import CategoricalDtype
    from ._enhanced_table import _QTableViewEnhanced


class TableItemDelegate(QtW.QStyledItemDelegate):
    """Displays table widget items with properly formatted numbers."""

    def __init__(self, parent: QtCore.QObject | None = None, ndigits: int = 4) -> None:
        super().__init__(parent)
        self.ndigits = ndigits
        self._parent = parent

    def replace(self, parent: QtCore.QObject | None = None) -> TableItemDelegate:
        return TableItemDelegate(parent, self.ndigits)

    def displayText(self, value, locale):
        return super().displayText(self._format_number(value), locale)

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
                line = QCellLineEdit(parent, table, (row, col))
                line.setFont(font)
                return line

            dtype: np.dtype = df.dtypes.values[col]
            if dtype == "category":
                # use combobox for categorical data
                dtype: CategoricalDtype
                cbox = QtW.QComboBox(parent)
                cbox.setFont(font)
                choices = list(map(str, dtype.categories))
                cbox.addItems(choices)
                cbox.setCurrentIndex(choices.index(df.iat[row, col]))
                cbox.currentIndexChanged.connect(qtable_view.setFocus)
                return cbox
            elif dtype == "bool":
                # use checkbox for boolean data
                cbox = QtW.QComboBox(parent)
                cbox.setFont(font)
                choices = ["True", "False"]
                cbox.addItems(choices)
                cbox.setCurrentIndex(0 if df.iat[row, col] else 1)
                cbox.currentIndexChanged.connect(qtable_view.setFocus)
                return cbox
            elif dtype.kind == "M":
                dt = QtW.QDateTimeEdit(parent)
                dt.setFont(font)
                val = df.iat[row, col]
                dt.setDateTime(val.to_pydatetime())
                return dt
            else:
                line = QCellLineEdit(parent, table, (row, col))
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
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ) -> None:
        if isinstance(editor, QtW.QDateTimeEdit):
            editor = cast(QtW.QDateTimeEdit, editor)
            dt = editor.dateTime().toPyDateTime()
            model.setData(index, dt, Qt.ItemDataRole.EditRole)
        else:
            return super().setModelData(editor, model, index)

    # modified from magicgui
    def _format_number(self, text: str) -> str:
        """convert string to int or float if possible"""
        try:
            value = int(text)
        except ValueError:
            try:
                value = float(text)
            except ValueError:
                return text

        ndigits = self.ndigits

        if isinstance(value, int):
            if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
                text = str(value)
            else:
                text = f"{value:.{ndigits-1}e}"

        elif isinstance(value, float):
            if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
                text = f"{value:.{ndigits}f}"
            else:
                text = f"{value:.{ndigits-1}e}"

        return text

    def initStyleOption(
        self, option: QtW.QStyleOptionViewItem, index: QtCore.QModelIndex
    ):
        super().initStyleOption(option, index)
        if option.state & QtW.QStyle.StateFlag.State_HasFocus:
            option.state = option.state & ~QtW.QStyle.StateFlag.State_HasFocus
