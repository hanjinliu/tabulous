from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from ..._keymap import QtKeys

from ._table_base import QBaseTable, QMutableTable, _QTableViewEnhanced

if TYPE_CHECKING:
    import numpy as np


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
                qtable_view._font, qtable_view._font_size * qtable_view.zoom()
            )
            if row >= df.shape[0] or col >= df.shape[1]:
                line = QDtypedLineEdit(parent, table, (row, col))
                line.setFont(font)
                return line

            dtype: np.dtype = df.dtypes.values[col]
            if dtype == "category":
                # use combobox for categorical data
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
                dt.setDateTime(df.iat[row, col].to_pydatetime())
                return dt
            else:
                line = QDtypedLineEdit(parent, table, (row, col))
                line.setFont(font)
                return line

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


class QDtypedLineEdit(QtW.QLineEdit):
    def __init__(
        self,
        parent: QtCore.QObject | None = None,
        table: QMutableTable | None = None,
        pos: tuple[int, int] = (0, 0),
    ):
        super().__init__(parent)
        self._table = table
        self._pos = pos
        self.textChanged.connect(self.onTextChanged)

    def isTextValid(self, r: int, c: int, text: str) -> bool:
        """True if text is valid for this cell."""
        try:
            self._table.convertValue(r, c, text)
        except Exception:
            return False
        return True

    def onTextChanged(self, text: str):
        """Change text color to red if invalid."""
        palette = QtGui.QPalette()
        table = self._table
        try:
            table.convertValue(self._pos[0], self._pos[1], text)
        except Exception:
            col = Qt.GlobalColor.red
        else:
            col = Qt.GlobalColor.black

        palette.setColor(QtGui.QPalette.ColorRole.Text, col)
        self.setPalette(palette)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle key press events."""
        keys = QtKeys(event)
        pos = self.cursorPosition()
        nchar = len(self.text())
        r, c = self._pos
        if pos == 0 and keys == "Left" and c > 0:
            self._table._qtable_view.setFocus()
            index = self._table._qtable_view.model().index(r, c - 1)
            self._table._qtable_view.setCurrentIndex(index)
        elif (
            pos == nchar
            and keys == "Right"
            and c < self._table.model().columnCount() - 1
        ):
            self._table._qtable_view.setFocus()
            index = self._table._qtable_view.model().index(r, c + 1)
            self._table._qtable_view.setCurrentIndex(index)
        return super().keyPressEvent(event)

    if TYPE_CHECKING:

        def parent(self) -> _QTableViewEnhanced:
            ...
