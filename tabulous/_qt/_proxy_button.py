from __future__ import annotations

from pathlib import Path
import logging
import ast
from typing import TYPE_CHECKING, Sequence
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal

from tabulous._qt._toolbar._toolbutton import QColoredToolButton
from tabulous._sort_filter_proxy import (
    FilterType,
    FilterInfo,
    ComposableFilter,
    ComposableSorter,
)
from superqt import QEnumComboBox

from tabulous.exceptions import UnreachableError

if TYPE_CHECKING:
    from typing_extensions import Self
    from tabulous._qt._table import QBaseTable
    import pandas as pd

ICON_DIR = Path(__file__).parent / "_icons"
logger = logging.getLogger("tabulous")


class HeaderAnchorMixin:
    @classmethod
    def install_to_table(cls, table: QBaseTable, index: int, *args, **kwargs) -> Self:
        """Install this widget to table at index."""
        with table._mgr.merging():
            self = cls(*args, **kwargs)
            table.setHorizontalHeaderWidget(index, self)
        return self

    def on_installed(self, table: QBaseTable, index: int):
        """Callback when this widget is installed to table header."""

    def on_uninstalled(self, table: QBaseTable, index: int):
        """Callback when this widget is uninstalled"""


class _QHeaderSectionButton(QColoredToolButton, HeaderAnchorMixin):
    def __init__(self, parent: QtW.QWidget = None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        eff = QtW.QGraphicsOpacityEffect()
        self._opacity = 0.3
        eff.setOpacity(self._opacity)
        self.setGraphicsEffect(eff)
        self._effect = eff

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self._effect.setOpacity(1.0)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._effect.setOpacity(self._opacity)

    def updateColorByBackground(self, bg: QtGui.QColor):
        whiteness = bg.red() + bg.green() + bg.blue()
        self._white_background = whiteness > 128 * 3
        if self._white_background:
            self.updateColor("#1E1E1E")
        else:
            self.updateColor("#CCCCCC")


class QHeaderSortButton(_QHeaderSectionButton):
    sortSignal = Signal(bool)
    resetSignal = Signal()

    def __init__(self, parent: QtW.QWidget = None, ascending: bool = True):
        super().__init__(parent)

        self.setIcon(ICON_DIR / "sort_table.svg")
        self._ascending = ascending
        self.clicked.connect(self._toggle)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.setToolTip("Sort by this column (right click to reset)")

    def _toggle(self):
        self._ascending = not self._ascending
        self.sortSignal.emit(self._ascending)

    def _show_menu(self, pos):
        menu = QtW.QMenu(self)
        menu.addAction("Reset", lambda: self.resetSignal.emit())
        menu.exec_(self.mapToGlobal(pos))

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
            elif f is None:
                table._set_proxy(ComposableSorter({index}, True))
            else:
                raise RuntimeError("Sort function is not a ComposableSorter.")

        def _reset():
            if isinstance(f, ComposableSorter):
                with table._mgr.merging(
                    lambda cmds: f"Remove sort button at index {index}"
                ):
                    table.setHorizontalHeaderWidget(index, None)
                    # table._set_proxy(f.decompose(index))
            else:
                raise RuntimeError("Sort function is not a ComposableSorter.")

        f = table._proxy._obj
        if not isinstance(f, ComposableSorter):
            f = ComposableSorter({index}, self.ascending())
        table._set_proxy(f.compose(index))
        self.sortSignal.connect(_sort)
        self.resetSignal.connect(_reset)
        if _viewer := table.parentViewer():
            self.updateColorByBackground(_viewer.backgroundColor())
        return None

    def on_uninstalled(self, table: QBaseTable, index: int):
        logger.debug(f"Uninstalling sort button at index {index}")
        self.sortSignal.disconnect()
        self.resetSignal.disconnect()
        f = table._proxy._obj
        if isinstance(f, ComposableSorter):
            table._set_proxy(f.decompose(index))
        return None


class QHeaderFilterButton(_QHeaderSectionButton):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setPopupMode(QtW.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setIcon(ICON_DIR / "filter.svg")
        self.setToolTip("Filter by this column")

    def on_installed(self, table: QBaseTable, index: int):
        logger.debug(f"Installing filter at index {index}")

        def _filter(info: FilterInfo):
            f = table._proxy._obj
            if isinstance(f, ComposableFilter):
                table._set_proxy(f.compose(index, info))
            elif f is None:
                table._set_proxy(ComposableFilter({index: info}))
            else:
                raise RuntimeError("Current proxy is not a ComposableFilter.")
            # TODO: this is incompatible with undo/redo
            # self._opacity = 0.3 if info.type is FilterType.none else 0.7
            # self._effect.setOpacity(self._opacity)
            return None

        def _reset():
            f = table._proxy._obj
            if isinstance(f, ComposableFilter):
                with table._mgr.merging(
                    lambda cmds: f"Remove filter button at index {index}"
                ):
                    table.setHorizontalHeaderWidget(index, None)
                    table._set_proxy(f.decompose(index))
            else:
                raise RuntimeError("Sort function is not a ComposableFilter.")

        f = table._proxy._obj
        if not isinstance(f, ComposableFilter):
            table._set_proxy(ComposableFilter())
        column = table.model().df.columns[index]
        menu = _QFilterMenu(table._get_sub_frame(column), parent=self)
        self.setMenu(menu)
        menu._filter_widget.called.connect(_filter)
        menu._filter_widget.reset.connect(_reset)
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
        self._filter_widget.reset.connect(self.hide)
        action.setDefaultWidget(self._filter_widget)
        self.addAction(action)
        self._filter_widget.requireResize.connect(self.resize)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        self._filter_widget._cbox.setFocus()
        return super().showEvent(a0)


class _QFilterWidget(QtW.QWidget):
    called = Signal(FilterInfo)
    reset = Signal()
    requireResize = Signal(QtCore.QSize)

    def __init__(self, ds: pd.Series, parent: QtW.QWidget = None):
        super().__init__(parent)
        self.setMinimumWidth(150)
        self._ds = ds
        self._cbox = QEnumComboBox(enum_class=FilterType)
        self._cbox.setMinimumWidth(100)
        self._cbox.setFont(QtGui.QFont("Arial", 10))
        self._value_edit = QtW.QLineEdit()
        self._string_edit = QtW.QLineEdit()
        self._value_edit.setFixedWidth(84)
        self._string_edit.setFixedWidth(84)
        self._unique_select = QMultiCheckBoxes()
        self._call_button = QtW.QPushButton("Apply")
        self._call_button.setToolTip("Apply filter to the column")
        self._reset_button = QtW.QPushButton("Reset")
        self._reset_button.setToolTip("Reset the filter of the column")
        self._setup_ui()

        self._cbox.currentEnumChanged.connect(self._type_changed)
        self._call_button.clicked.connect(self._call_button_clicked)
        self._reset_button.clicked.connect(lambda: self.reset.emit())
        self._type_changed(FilterType.none)

    def _type_changed(self, val: FilterType):
        self._value_edit.setVisible(False)
        self._string_edit.setVisible(False)
        self._unique_select.setVisible(False)
        if val.requires_list:
            self._unique_select.setVisible(True)
            self._unique_select.setChoices(self.fetch_unique())
        elif val.requires_number:
            self._value_edit.setVisible(True)
            self._value_edit.setFocus()
        elif val.requires_text:
            self._string_edit.setVisible(True)
            self._string_edit.setFocus()
        elif val is not FilterType.none:
            raise UnreachableError(f"Unreachable: {val}")
        self.requireResize.emit(self.sizeHint())

    def _call_button_clicked(self):
        return self.called.emit(self.get_filter_info())

    def get_filter_info(self) -> FilterInfo:
        ftype: FilterType = self._cbox.currentEnum()
        if ftype.requires_number:
            arg = ast.literal_eval(self._value_edit.text())
        elif ftype.requires_text:
            arg = self._string_edit.text()
        elif ftype.requires_list:
            arg = self._unique_select.value()
        else:
            arg = None
        return FilterInfo(ftype, arg)

    def fetch_unique(self):
        unique = self._ds.unique()
        if len(unique) > 108:
            raise ValueError("Too many unique values")
        return unique

    def _setup_ui(self):
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(2, 2, 2, 2)

        _layout.addWidget(QtW.QLabel("Filter by:"))

        _middle = QtW.QWidget()
        _middle_layout = QtW.QHBoxLayout()
        _middle_layout.setContentsMargins(0, 0, 0, 0)
        _middle_layout.addWidget(self._cbox, alignment=Qt.AlignmentFlag.AlignLeft)
        _middle_layout.addWidget(
            self._value_edit, alignment=Qt.AlignmentFlag.AlignRight
        )
        _middle_layout.addWidget(
            self._string_edit, alignment=Qt.AlignmentFlag.AlignRight
        )
        _middle.setLayout(_middle_layout)

        _layout.addWidget(_middle)
        _layout.addWidget(self._unique_select)

        _bottom = QtW.QWidget()
        _bottom_layout = QtW.QHBoxLayout()
        _bottom_layout.setContentsMargins(0, 0, 0, 0)
        _bottom_layout.addWidget(self._call_button)
        _bottom_layout.addWidget(self._reset_button)
        _bottom.setLayout(_bottom_layout)
        _layout.addWidget(_bottom)
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
            item = QtW.QListWidgetItem()
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
