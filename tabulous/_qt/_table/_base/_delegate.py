from __future__ import annotations
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt
import numpy as np

from ._table_base import QBaseTable, QMutableTable


class TableItemDelegate(QtW.QStyledItemDelegate):
    """Displays table widget items with properly formatted numbers."""

    def __init__(self, parent: QtCore.QObject | None = None, ndigits: int = 4) -> None:
        super().__init__(parent)
        self.ndigits = ndigits

    def displayText(self, value, locale):
        return super().displayText(self._format_number(value), locale)

    def createEditor(
        self, parent: QtW.QWidget, option, index: QtCore.QModelIndex
    ) -> QtW.QWidget:
        """Create different type of editors for different dtypes."""
        qtable: QBaseTable = parent.parent()
        table = qtable.parent()
        if isinstance(table, QMutableTable):
            df = table.model().df
            row = index.row()
            col = index.column()
            if row >= df.shape[0] or col >= df.shape[1]:
                # out of bounds
                return super().createEditor(parent, option, index)

            dtype: np.dtype = df.dtypes.values[col]
            if dtype == "category":
                # use combobox for categorical data
                cbox = QtW.QComboBox(parent)
                choices = list(map(str, dtype.categories))
                cbox.addItems(choices)
                cbox.setCurrentIndex(choices.index(df.iat[row, col]))
                cbox.currentIndexChanged.connect(qtable.setFocus)
                return cbox
            elif dtype == "bool":
                # use checkbox for boolean data
                cbox = QtW.QComboBox(parent)
                choices = ["True", "False"]
                cbox.addItems(choices)
                cbox.setCurrentIndex(0 if df.iat[row, col] else 1)
                cbox.currentIndexChanged.connect(qtable.setFocus)
                return cbox
            elif dtype.kind == "M":
                dt = QtW.QDateTimeEdit(parent)
                dt.setDateTime(df.iat[row, col].to_pydatetime())
                return dt

        return super().createEditor(parent, option, index)

    def setEditorData(self, editor: QtW.QWidget, index: QtCore.QModelIndex) -> None:
        super().setEditorData(editor, index)
        if isinstance(editor, QtW.QComboBox):
            editor.showPopup()
        return None

    def setModelData(
        self,
        editor: QtW.QWidget,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ) -> None:
        if isinstance(editor, QtW.QDateTimeEdit):
            dt = editor.dateTime().toPyDateTime()
            model.setData(index, dt, Qt.ItemDataRole.EditRole)
        else:
            return super().setModelData(editor, model, index)

    # modified from magicgui
    def _format_number(self, text: str) -> str:
        """convert string to int or float if possible"""
        try:
            value: int | float | None = int(text)
        except ValueError:
            try:
                value = float(text)
            except ValueError:
                value = None

        ndigits = self.ndigits

        if isinstance(value, (int, float)):
            if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
                text = str(value) if isinstance(value, int) else f"{value:.{ndigits}f}"
            else:
                text = f"{value:.{ndigits-1}e}"

        return text
