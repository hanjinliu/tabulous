from __future__ import annotations
from typing import Any, Callable, Hashable, TYPE_CHECKING
import warnings
from qtpy import QtCore, QtGui, QtWidgets as QtW
from qtpy.QtCore import Qt, Signal
import pandas as pd

from ._line_edit import QCellLiteralEdit
from tabulous._dtype import isna
from tabulous.color import normalize_color, ColorType
from tabulous._text_formatter import DefaultFormatter
from tabulous._map_model import TableMapping

if TYPE_CHECKING:
    from ._table_base import QBaseTable

# https://ymt-lab.com/post/2020/pyqt5-qtableview-pandas-qabstractitemmodel/

_READ_ONLY = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


class AbstractDataFrameModel(QtCore.QAbstractTableModel):
    """Table model for data frame."""

    dataEdited = Signal(int, int, object)
    _FORMAT_ERROR = "<Format Error>"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df = pd.DataFrame([])

        self._editable = False
        self._foreground_colormap: dict[Hashable, Callable[[Any], ColorType]] = {}
        self._background_colormap: dict[Hashable, Callable[[Any], ColorType]] = {}
        self._text_formatter: dict[Hashable, Callable[[Any], str]] = {}
        self._validator: dict[Hashable, Callable[[Any], None]] = {}

        self._data_role_map = {
            Qt.ItemDataRole.DisplayRole: self._data_display,
            Qt.ItemDataRole.EditRole: self._data_edit,
            Qt.ItemDataRole.TextColorRole: self._data_text_color,
            Qt.ItemDataRole.ToolTipRole: self._data_tooltip,
            Qt.ItemDataRole.BackgroundColorRole: self._data_background_color,
            Qt.ItemDataRole.DecorationRole: self._data_decoration,
        }

        self._decorations: TableMapping[tuple[QtGui.QPixmap, str]] = TableMapping()

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def updateValue(self, r, c, val):
        # pandas warns but no problem
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._df.iloc[r, c] = val

    def data(
        self,
        index: QtCore.QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return QtCore.QVariant()
        if map := self._data_role_map.get(role, None):
            return map(index)
        return QtCore.QVariant()

    def _data_display(self, index: QtCore.QModelIndex):
        """Display role."""
        r, c = index.row(), index.column()
        df = self.df
        if r < df.shape[0] and c < df.shape[1]:
            val = df.iat[r, c]
            colname = df.columns[c]
            if isna(val):
                text = "NA"
            elif mapper := self._text_formatter.get(colname, None):
                try:
                    text = str(mapper(val))
                except Exception:
                    text = self._FORMAT_ERROR
            else:
                fmt = DefaultFormatter(df.dtypes[colname])
                text = fmt(val)
            return text
        return QtCore.QVariant()

    def _data_edit(self, index: QtCore.QModelIndex):
        """Edit role."""
        r, c = index.row(), index.column()
        df = self.df
        if r < df.shape[0] and c < df.shape[1]:
            base_table = self.parent()
            if ref_expr := base_table._get_ref_expr(r, c):
                return QCellLiteralEdit._REF_PREFIX + ref_expr

            val = df.iat[r, c]
            if isna(val):
                text = "NA"
            else:
                text = str(val)
            return text
        return QtCore.QVariant()

    def _data_text_color(self, index: QtCore.QModelIndex):
        if not self._foreground_colormap:
            return QtCore.QVariant()
        r, c = index.row(), index.column()
        df = self.df
        if r < df.shape[0] and c < df.shape[1]:
            colname = df.columns[c]
            val = df.iat[r, c]
            if mapper := self._foreground_colormap.get(colname, None):
                # If mapper is given for the column, call it.
                try:
                    col = mapper(val)
                    if col is None:
                        if isna(val):
                            return QtGui.QColor(Qt.GlobalColor.gray)
                        return QtCore.QVariant()
                    rgba = normalize_color(col)
                except Exception as e:
                    # since this method is called many times, errorous function should be
                    # deleted from the mapper.
                    self._foreground_colormap.pop(colname)
                    raise e
                return QtGui.QColor(*rgba)
            if isna(val):
                return QtGui.QColor(Qt.GlobalColor.gray)
        return QtCore.QVariant()

    def _data_tooltip(self, index: QtCore.QModelIndex):
        r, c = index.row(), index.column()
        if r < self.df.shape[0] and c < self.df.shape[1]:
            val = self.df.iat[r, c]
            dtype = self.df.dtypes.values[c]
            if ref_expr := self.parent()._get_ref_expr(r, c):
                ref = f"\nExpr: {ref_expr}"
            else:
                ref = ""
            if dtype != object:
                return f"{val!r} (dtype: {dtype}){ref}"
            else:
                return f"{val!r} (dtype: {dtype}; type: {type(val).__name__}){ref}"
        return QtCore.QVariant()

    def _data_background_color(self, index: QtCore.QModelIndex):
        if not self._background_colormap:
            return QtCore.QVariant()
        r, c = index.row(), index.column()
        df = self.df
        if r < df.shape[0] and c < df.shape[1]:
            colname = df.columns[c]
            if mapper := self._background_colormap.get(colname, None):
                val = df.iat[r, c]
                try:
                    col = mapper(val)
                    if col is None:
                        return QtCore.QVariant()
                    rgba = normalize_color(col)
                except Exception as e:
                    # since this method is called many times, errorous function should be
                    # deleted from the mapper.
                    self._background_colormap.pop(colname)
                    raise e
                return QtGui.QColor(*rgba)
        return QtCore.QVariant()

    def _data_decoration(self, index: QtCore.QModelIndex):
        r, c = index.row(), index.column()
        if content := self._decorations.get((r, c), None):
            return content[0]
        return QtCore.QVariant()

    def set_cell_label(self, index: QtCore.QModelIndex, text: str | None):
        if text is None:
            self._decorations.pop((index.row(), index.column()), None)
        else:
            qlabel = QtW.QLabel(text, self.parent())
            qlabel.setStyleSheet("background-color: transparent; color: gray;")
            qlabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            from tabulous._utils import get_config

            table_config = get_config().table
            font = QtGui.QFont(table_config.font, table_config.font_size)
            font.setBold(True)
            qlabel.setFont(font)
            rect = QtGui.QFontMetrics(font).boundingRect(text)
            qlabel.resize(rect.size())
            pixmap = qlabel.grab()
            qlabel.deleteLater()
            self._decorations[(index.row(), index.column())] = pixmap, text
        qtable_view = self.parent()._qtable_view
        qtable_view.update(index)
        return None

    def flags(self, index):
        if self._editable:
            return Qt.ItemFlag.ItemIsEditable | _READ_ONLY
        else:
            return _READ_ONLY

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                if section >= self.df.columns.size:
                    return None
                if self.df.columns.nlevels == 1:
                    text = str(self.df.columns[section])
                else:
                    text = "\n".join(map(str, self.df.columns[section]))
                return text
            elif role == Qt.ItemDataRole.ToolTipRole:
                if section < self.df.columns.size:
                    return self._column_tooltip(section)
                return None

        if orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DisplayRole:
                if section >= self.df.index.size:
                    return None
                text = str(self.df.index[section])
                return text
            elif role == Qt.ItemDataRole.ToolTipRole:
                if section < self.df.index.size:
                    return str(self.df.index[section])
                return None

    def _column_tooltip(self, section: int):
        name = self.df.columns[section]
        dtype = self.df.dtypes.values[section]
        return f"{name} (dtype: {dtype})"

    def delete_column(self, name: str):
        """Delete keys to match new columns."""
        self._foreground_colormap.pop(name, None)
        self._background_colormap.pop(name, None)
        self._text_formatter.pop(name, None)
        self._validator.pop(name, None)
        return None

    def rename_column(self, old_name: str, new_name: str):
        """Fix keys to match new column names."""
        if background_colormap := self._background_colormap.pop(old_name, None):
            self._background_colormap[new_name] = background_colormap
        if foreground_colormap := self._foreground_colormap.pop(old_name, None):
            self._foreground_colormap[new_name] = foreground_colormap
        if text_formatter := self._text_formatter.pop(old_name, None):
            self._text_formatter[new_name] = text_formatter
        if validator := self._validator.pop(old_name, None):
            self._validator[new_name] = validator
        return None

    def setData(self, index: QtCore.QModelIndex, value, role) -> bool:
        if not index.isValid():
            return False
        if role != Qt.ItemDataRole.EditRole:
            return False
        r, c = index.row(), index.column()
        self.dataEdited.emit(r, c, value)
        return True

    def setShape(self, nrow: int, ncol: int):
        """Set table shape."""
        r0, c0 = self.rowCount(), self.columnCount()
        dr = nrow - r0
        dc = ncol - c0

        # Adjust rows
        parent = QtCore.QModelIndex()
        if dr > 0:
            self.beginInsertRows(parent, r0, r0 + dr - 1)
            self.insertRows(r0, dr, parent)
            self.endInsertRows()
        elif dr < 0:
            self.beginRemoveRows(parent, r0 + dr, r0 - 1)
            self.removeRows(r0 + dr, -dr, parent)
            self.endRemoveRows()

        # Adjust columns
        if dc > 0:
            self.beginInsertColumns(parent, c0, c0 + dc - 1)
            self.insertColumns(c0, dc, parent)
            self.endInsertColumns()
        elif dc < 0:
            self.beginRemoveColumns(parent, c0 + dc, c0 - 1)
            self.removeColumns(c0 + dc, -dc, parent)
            self.endRemoveColumns()

        return None

    def insertColumns(
        self, column: int, count: int, parent: QtCore.QModelIndex = None
    ) -> bool:
        self._decorations.insert_columns(column, count)
        return super().insertColumns(column, count, parent)

    def removeColumns(
        self, column: int, count: int, parent: QtCore.QModelIndex = None
    ) -> bool:
        self._decorations.remove_columns(column, count)
        return super().removeColumns(column, count, parent)

    def insertRows(
        self, row: int, count: int, parent: QtCore.QModelIndex = None
    ) -> bool:
        self._decorations.insert_rows(row, count)
        return super().insertRows(row, count, parent)

    def removeRows(
        self, row: int, count: int, parent: QtCore.QModelIndex = None
    ) -> bool:
        self._decorations.remove_rows(row, count)
        return super().removeRows(row, count, parent)

    if TYPE_CHECKING:

        def parent(self) -> QBaseTable:
            ...


class DataFrameModel(AbstractDataFrameModel):
    """A concrete model for a pandas DataFrame."""

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @df.setter
    def df(self, data: pd.DataFrame):
        if data is self._df:
            return
        self.setShape(*data.shape)
        self._df = data

    def rowCount(self, parent=None):
        return self.df.shape[0]

    def columnCount(self, parent=None):
        return self.df.shape[1]
