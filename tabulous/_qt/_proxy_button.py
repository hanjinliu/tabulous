from __future__ import annotations

from pathlib import Path
import logging
from typing import TYPE_CHECKING, Sequence
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal

from tabulous._sort_filter_proxy import ComposableFilter
from tabulous._qt._toolbar._toolbutton import QColoredToolButton
from tabulous._sort_filter_proxy import (
    FilterType,
    FilterInfo,
    ComposableFilter,
    ComposableSorter,
)
from magicgui.widgets import ComboBox

if TYPE_CHECKING:
    from tabulous._qt._table import QBaseTable
    import pandas as pd

ICON_DIR = Path(__file__).parent / "_icons"
logger = logging.getLogger("tabulous")


class _QHeaderSectionButton(QColoredToolButton):
    def __init__(self, parent: QtW.QWidget = None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        eff = QtW.QGraphicsOpacityEffect()
        eff.setOpacity(0.3)
        self.setGraphicsEffect(eff)
        self._effect = eff

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self._effect.setOpacity(1.0)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._effect.setOpacity(0.3)

    def updateColorByBackground(self, bg: QtGui.QColor):
        whiteness = bg.red() + bg.green() + bg.blue()
        self._white_background = whiteness > 128 * 3
        if self._white_background:
            self.updateColor("#1E1E1E")
        else:
            self.updateColor("#CCCCCC")


class QHeaderSortButton(_QHeaderSectionButton):
    sortSignal = Signal(bool)

    def __init__(self, parent: QtW.QWidget = None, ascending: bool = True):
        super().__init__(parent)

        self.setIcon(ICON_DIR / "sort_table.svg")
        self._ascending = ascending
        self.clicked.connect(self._toggle)

    def _toggle(self):
        self._ascending = not self._ascending
        self.sortSignal.emit(self._ascending)

    def ascending(self) -> bool:
        return self._ascending

    @classmethod
    def install_to_table(cls, table: QBaseTable, index: int, ascending: bool = True):
        with table._mgr.merging():
            self = cls(ascending=ascending)
            table.setHorizontalHeaderWidget(index, self)
        return self

    def on_installed(self, table: QBaseTable, index: int):
        logger.debug(f"Installing sort button at index {index}")

        def _sort():
            f = table._proxy._obj
            if isinstance(f, ComposableSorter):
                table._set_proxy(f.switch())
            else:
                raise RuntimeError("Sort function is not a ComposableSorter.")

        f = table._proxy._obj
        if not isinstance(f, ComposableSorter):
            f = ComposableSorter({index}, self.ascending())
        table._set_proxy(f.compose(index))
        self.sortSignal.connect(_sort)
        if _viewer := table.parentViewer():
            self.updateColorByBackground(_viewer.backgroundColor())
        return None

    def on_uninstalled(self, table: QBaseTable, index: int):
        logger.debug(f"Uninstalling sort button at index {index}")
        self.sortSignal.disconnect()
        f = table._proxy._obj
        if isinstance(f, ComposableSorter):
            table._set_proxy(f.decompose(index))
        return None


class QHeaderFilterButton(_QHeaderSectionButton):
    def __init__(self, parent: QtW.QWidget = None):
        super().__init__(parent)
        self.setPopupMode(QtW.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setIcon(ICON_DIR / "filter.svg")

    @classmethod
    def install_to_table(cls, table: QBaseTable, index: int):
        with table._mgr.merging():
            self = cls()
            table.setHorizontalHeaderWidget(index, self)
        return self

    def on_installed(self, table: QBaseTable, index: int):
        logger.debug(f"Installing filter at index {index}")

        def _filter(info: FilterInfo):
            f = table._proxy._obj
            if isinstance(f, ComposableFilter):
                table._set_proxy(f.compose(info.type, index, info.arg))
            else:
                raise RuntimeError("Sort function is not a ComposableFilter.")
            return None

        f = table._proxy._obj
        if not isinstance(f, ComposableFilter):
            table._set_proxy(ComposableFilter())
        column = table.model().df.columns[index]
        menu = _QFilterMenu(table._get_sub_frame(column))
        self.setMenu(menu)
        menu._filter_widget.called.connect(_filter)
        if _viewer := table.parentViewer():
            self.updateColorByBackground(_viewer.backgroundColor())
        return None

    def on_uninstalled(self, table: QBaseTable, index: int):
        logger.debug(f"Uninstalling filter at index {index}")
        f = table._proxy._obj
        if isinstance(f, ComposableFilter):
            table._set_proxy(f.decompose(index))

        return None


class _QFilterMenu(QtW.QMenu):
    def __init__(self, ds: pd.Series, parent: QtW.QWidget = None):
        super().__init__(parent)
        self._ds = ds
        action = QtW.QWidgetAction(self)
        self._filter_widget = _QFilterWidget(ds)
        self._filter_widget.called.connect(self.hide)
        action.setDefaultWidget(self._filter_widget)
        self.addAction(action)
        self._filter_widget.requireResize.connect(self.resize)


class _QFilterWidget(QtW.QWidget):
    called = Signal(FilterInfo)
    requireResize = Signal(QtCore.QSize)

    def __init__(self, ds: pd.Series, parent: QtW.QWidget = None):
        super().__init__(parent)
        self.setMinimumWidth(150)
        self._ds = ds
        self._cbox = ComboBox(
            value=FilterType.none, choices=[(a.repr, a) for a in FilterType]
        )
        self._cbox.min_width = 100
        self._cbox.native.setFont(QtGui.QFont("Arial", 10))
        self._value_edit = QtW.QLineEdit()
        self._string_edit = QtW.QLineEdit()
        self._value_edit.setFixedWidth(84)
        self._string_edit.setFixedWidth(84)
        self._unique_select = QMultiCheckBoxes()
        self._call_button = QtW.QPushButton("Apply")
        self._setup_ui()

        self._cbox.changed.connect(self._type_changed)
        self._call_button.clicked.connect(self._button_clicked)
        self._type_changed(FilterType.none)

    def _type_changed(self, val: FilterType):
        self._value_edit.setVisible(val.requires_number)
        self._string_edit.setVisible(val.requires_text)
        self._unique_select.setVisible(val.requires_list)
        if val.requires_list:
            self._unique_select.setChoices(self.fetch_unique())

        self.requireResize.emit(self.sizeHint())

    def _button_clicked(self):
        return self.called.emit(self.get_filter_info())

    def get_filter_info(self) -> FilterInfo:
        ftype: FilterType = self._cbox.value
        if ftype.requires_number:
            arg = float(self._value_edit.text())
        elif ftype.requires_text:
            arg = self._string_edit.text()
        elif ftype.requires_list:
            arg = self._unique_select.value()
        return FilterInfo(self._cbox.value, arg)

    def fetch_unique(self):
        unique = self._ds.unique()
        if len(unique) > 54:
            raise ValueError("Too many unique values")
        return unique

    def _setup_ui(self):
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(2, 2, 2, 2)

        _layout.addWidget(QtW.QLabel("Filter by:"))

        _middle = QtW.QWidget()
        _middle_layout = QtW.QHBoxLayout()
        _middle_layout.setContentsMargins(0, 0, 0, 0)
        _middle_layout.addWidget(
            self._cbox.native, alignment=Qt.AlignmentFlag.AlignLeft
        )
        _middle_layout.addWidget(
            self._value_edit, alignment=Qt.AlignmentFlag.AlignRight
        )
        _middle_layout.addWidget(
            self._string_edit, alignment=Qt.AlignmentFlag.AlignRight
        )
        _middle.setLayout(_middle_layout)

        _layout.addWidget(_middle)
        _layout.addWidget(self._unique_select)
        _layout.addWidget(self._call_button)
        self.setLayout(_layout)


class QMultiCheckBoxes(QtW.QListWidget):
    def __init__(self, parent: QtW.QWidget = None):
        super().__init__(parent)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.NoSelection)
        self.horizontalScrollBar().setVisible(False)
        self.setFixedHeight(120)
        self._choices = []

    def setChoices(self, choices: Sequence):
        self.clear()
        self._choices = choices
        for c in choices:
            text = repr(c)
            item = QtW.QListWidgetItem(text)
            self.addItem(item)
            checkbox = QtW.QCheckBox(text)
            checkbox.setChecked(False)
            self.setItemWidget(item, checkbox)
        return None

    def iter_items(self):
        for i in range(self.count()):
            yield self.item(i)

    def value(self) -> list:
        return [
            self._choices[i]
            for i in range(self.count())
            if self.itemWidget(self.item(i)).isChecked()
        ]

    if TYPE_CHECKING:

        def itemWidget(self, item: QtW.QListWidgetItem) -> QtW.QCheckBox:
            ...
