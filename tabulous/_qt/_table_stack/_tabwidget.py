from __future__ import annotations
from typing import Literal, TYPE_CHECKING, cast
import weakref
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal

from tabulous._qt._table_stack._start import QStartupWidget
from tabulous._qt._table_stack._utils import create_temporal_line_edit

from tabulous._qt._table._base._table_group import QTableGroup
from tabulous._qt._clickable_label import QClickableLabel
from tabulous._qt._action_registry import QActionRegistry

if TYPE_CHECKING:
    from tabulous._qt._table import QBaseTable, QMutableTable
    from tabulous._qt._mainwindow._base import _QtMainWidgetBase
    from tabulous._qt._table_stack._overlay import QOverlayWidget


class QTabbedTableStack(QtW.QTabWidget, QActionRegistry[int]):
    """Tab widget used for table stack."""

    currentTableChanged = Signal(int)  # index
    itemDropped = Signal(object)  # dropped item info
    itemMoved = Signal(int, int)  # source index, destination index
    tableRenamed = Signal(int, str)  # index
    tableRemoved = Signal(int)  # index
    tablePassed = Signal(object, int, object)  # source widget, tab_id, target widget
    resizedSignal = Signal()

    def __init__(
        self,
        parent=None,
        tab_position: str = "top",
    ):
        QtW.QTabWidget.__init__(self, parent)
        QActionRegistry.__init__(self)

        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )

        from . import _tabbar

        if tab_position == "top":
            self.setTabBar(_tabbar.QTabulousTabBar(self))
        elif tab_position == "left":
            self.setTabBar(_tabbar.QLeftSideBar(self))
            self.setTabPosition(QtW.QTabWidget.TabPosition.West)
        elif tab_position == "bottom":
            self.setTabBar(_tabbar.QTabulousTabBar(self))
            self.setTabPosition(QtW.QTabWidget.TabPosition.South)
        elif tab_position == "right":
            self.setTabBar(_tabbar.QRightSideBar(self))
            self.setTabPosition(QtW.QTabWidget.TabPosition.East)
        else:
            raise ValueError(f"Unknown position {tab_position!r}.")

        self.setAcceptDrops(True)
        self.setMovable(True)

        self.tabBar().customContextMenuRequested.connect(self.showContextMenu)
        self.currentChanged.connect(self.currentTableChanged.emit)
        self.tabCloseRequested.connect(self.takeTable)
        self.tabCloseRequested.connect(self.tableRemoved.emit)
        # NOTE: arguments are not (from, to). Bug in Qt??
        self.tabBar().tabMoved.connect(lambda a, b: self.itemMoved.emit(b, a))
        self.tabBarDoubleClicked.connect(self.enterEditingMode)

        # NOTE: this is needed to correctly refocus table groups.
        self.tabBarClicked.connect(self.setCurrentIndex)

        # add overlay widget
        from ._overlay import QOverlayWidget

        self._overlay = QOverlayWidget(self)
        self._notifier = QOverlayWidget(self, duration=200)
        self._notifier.setAnchor("top_right")

        # temporal QLineEdit for editing tabs
        self._line: QtW.QLineEdit | None = None

        self._entering_tab_index: int | None = None

        # "new tab" button
        tb = QtW.QToolButton()
        tb.setText("+")
        tb.setFont(QtGui.QFont("Arial", 12, weight=15))
        tb.setToolTip("New spreadsheet")
        tb.clicked.connect(lambda: self.parent()._table_viewer.add_spreadsheet())
        self.setCornerWidget(tb)
        self.addEmptyWidget()

    # fmt: off
    if TYPE_CHECKING:
        def parent(self) -> _QtMainWidgetBase: ...
        def parentWidget(self) -> _QtMainWidgetBase: ...
    # fmt: on

    def addEmptyWidget(self):
        """Add empty widget to stack."""
        assert self.count() == 0
        startup = QStartupWidget()
        self.addTab(startup, "")
        self.tabBar().hide()
        return

    def isEmpty(self) -> bool:
        return self.count() == 1 and isinstance(self.widget(0), QStartupWidget)

    def addTable(self, table: QBaseTable, name: str = "None"):
        """Add `table` to stack as name `name`."""
        if self.isEmpty():
            self.removeTab(0)
            self.tabBar().show()
        self.addTab(table, name)
        table._qtable_view.resizedSignal.connect(self.resizedSignal.emit)
        return None

    def takeTable(self, index: int) -> QBaseTable:
        """Remove table at `index` and return it."""
        table = self.tableAtIndex(index)
        self.untileTable(index)
        self.removeTab(index)
        if self.count() == 0:
            self.addEmptyWidget()
        else:
            self.parentWidget().setCellFocus()
        return table

    def renameTable(self, index: int, name: str):
        """Rename table at `index` to `name`."""
        return self.setTabText(index, name)

    def tableIndex(self, table: QBaseTable) -> int:
        """Get the index of `table`."""
        for i in range(self.count()):
            data = self.tableAtIndex(i)
            if data is table:
                break
        else:
            raise ValueError(f"Table {table!r} not found.")
        return i

    def tableAtIndex(self, i: int) -> QBaseTable:
        """Get the table at `i`."""
        wdt = self.widget(i)
        if isinstance(wdt, QStartupWidget):
            return None
        if isinstance(wdt, QTableGroup):
            wdt = cast(QTableGroup, wdt)
            idx = self._tab_index_to_group_index(i)
            return wdt.tables[idx]
        return wdt

    def tableAt(self, pos: QtCore.QPoint) -> QBaseTable | None:
        """Return table at position."""
        index = self.tabBar().tabAt(pos)
        # TODO: bug when position is east or south
        if index == -1:
            return None
        return self.tableAtIndex(index)

    def moveTable(self, src: int, dst: int):
        """Move table from `src` to `dst`."""
        return self.tabBar().moveTab(src, dst)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        # This override is necessary for accepting drops from files.
        e.accept()
        source = e.source()
        if source is None:
            return
        if source.parent() is not self:
            return

        self._entering_tab_index = self.indexOf(self.widget(self._moving_tab_index))
        return None

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        mime = e.mimeData()
        text = mime.text()
        if text:
            # File is dropped.
            for path in text.splitlines():
                if path:
                    # properly format path
                    if path.startswith("file:///"):
                        # NOTE: this is needed! lstrip-only does not work
                        path = path.lstrip("file:///")
                    elif path.startswith("file:"):
                        path = path.lstrip("file:")
                    self.itemDropped.emit(path)

        source = e.source()
        if source is None:
            return
        source_widget: QTabbedTableStack = source.parent()
        if not isinstance(source_widget, QTabbedTableStack):
            return
        tab_id = source_widget._entering_tab_index
        if source_widget is self:
            return super().dropEvent(e)
        if tab_id is None:
            return None
        # Tab from other stack is dropped.
        e.setDropAction(Qt.DropAction.MoveAction)
        e.accept()

        self.tablePassed.emit(source_widget, tab_id, self)
        return super().dropEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self.isEmpty():
            return
        self._startDrag(e.pos())

    def _startDrag(self, pos: QtCore.QPoint):
        pos_global = self.mapToGlobal(pos)
        tabbar = self.tabBar()
        pos_intab = tabbar.mapFromGlobal(pos_global)
        self._moving_tab_index = tabbar.tabAt(pos)
        if self._moving_tab_index < 0:
            return

        tabrect = self.tabRect(self._moving_tab_index)

        pixmap = QtGui.QPixmap(tabrect.size())
        tabbar.render(pixmap, QtCore.QPoint(), QtGui.QRegion(tabrect))
        mime = QtCore.QMimeData()
        drag = QtGui.QDrag(tabbar)
        drag.setMimeData(mime)
        drag.setPixmap(pixmap)
        cursor = QtGui.QCursor(Qt.CursorShape.OpenHandCursor)
        drag.setHotSpot(pos - pos_intab)
        drag.setDragCursor(cursor.pixmap(), Qt.DropAction.MoveAction)
        drag.exec_(Qt.DropAction.MoveAction)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if self._line is not None:
            self._line.setHidden(True)
        return super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        return super().mouseDoubleClickEvent(e)

    def dragLeaveEvent(self, e: QtGui.QDragLeaveEvent):
        e.accept()
        return None

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        self.resizedSignal.emit()
        return super().resizeEvent(e)

    def tabRect(self, index: int):
        """Get QRect of the tab at index."""
        rect = self.tabBar().tabRect(index)

        # NOTE: East/South tab returns wrong value (Bug in Qt?)
        if self.tabPosition() == QtW.QTabWidget.TabPosition.East:
            w = self.rect().width() - rect.width()
            rect.translate(w, 0)
        elif self.tabPosition() == QtW.QTabWidget.TabPosition.South:
            h = self.rect().height() - rect.height()
            rect.translate(0, h)

        return rect

    def enterEditingMode(self, index: int):
        """Enter edit table name mode."""
        if self.isEmpty():
            return
        rect = self.tabRect(index)

        # set geometry
        line = create_temporal_line_edit(rect, self, self.tabText(index))
        self._line = line

        @self._line.editingFinished.connect
        def _():
            self._line.setHidden(True)
            text = self._line.text()
            if text:
                # do not rename if text is empty
                self.setTabText(index, text)
                self.tableRenamed.emit(index, text)
            self.parentWidget().setCellFocus()

        return None

    def showContextMenu(self, pos: QtCore.QPoint) -> None:
        """Execute contextmenu."""
        table = self.tableAt(pos)
        if table is None:
            return
        index = self.tableIndex(table)
        return self.execContextMenu(self.mapToGlobal(pos), index)

    def notifyEditability(self):
        """Show a notification saying that the table is not editable."""
        idx = self.currentIndex()
        qtable = self.tableAtIndex(idx)
        name = self.tabText(idx)
        return self.notifyByWidget(QEditabilityNotifier(qtable, name))

    def notifyLatestVersion(self, version: str):
        return self.notifyByWidget(QLatestVersionNotifier(version))

    def notifyByWidget(self, widget: QtW.QWidget):
        self._notifier.addWidget(widget)
        self._notifier.show()
        self._notifier.hideLater()
        return None

    def setCurrentIndex(self, index: int):
        """Set current active index."""
        wdt = self.widget(index)
        if isinstance(wdt, QTableGroup):
            wdt = cast(QTableGroup, wdt)
            wdt.setFocusedIndex(self._tab_index_to_group_index(index))
        return super().setCurrentIndex(index)

    def tileTables(
        self,
        indices: list[int],
        orientation: Literal["horizontal", "vertical"] = "horizontal",
    ):
        """Merge tables at indices."""
        # strict check of indices
        if len(indices) < 2:
            raise ValueError("Need at least two tables to merge.")
        elif not all(0 <= idx < self.count() for idx in indices):
            raise IndexError("Table indices out of range.")
        elif not all(isinstance(idx, int) for idx in indices):
            raise TypeError("Indices must be integers.")
        elif len(set(indices)) != len(indices):
            raise ValueError("Duplicate indices.")

        # check orientation
        if orientation == "horizontal":
            ori = Qt.Orientation.Horizontal
        elif orientation == "vertical":
            ori = Qt.Orientation.Vertical
        else:
            raise ValueError("Orientation must be 'horizontal' or 'vertical'.")

        current_index = self.currentIndex()
        indices = sorted(indices)

        # untile tables before tiling with others
        tables: list[QBaseTable] = []
        for i in indices:
            table = self.widget(i)
            if isinstance(table, QTableGroup):
                table = self.untileTable(i)
            tables.append(table)
        group = QTableGroup(tables, ori)

        for index in indices:
            self.replaceWidget(index, group.copy())

        self.setCurrentIndex(current_index)
        return None

    def tiledIndices(self, idx: int) -> list[int]:
        """Return indices of tables that are tiled with one at idx."""
        wdt = self.widget(idx)
        if isinstance(wdt, QTableGroup):
            wdt = cast(QTableGroup, wdt)
            return [self.tableIndex(table) for table in wdt.tables]
        else:
            return [idx]

    def replaceWidget(self, index: int, new: QtW.QWidget) -> None:
        """
        Replace table at index with new table.

        This function will NOT consider if the incoming and to-be-replaced tables
        are table group or not. This function is genuinely a method of QTabWidget.

        Parameters
        ----------
        index : int
            Index of the widget to be replaced.
        new : QWidget
            New widget to replace the old one.
        """
        text = self.tabText(index)
        self.removeTab(index)
        self.insertTab(index, new, text)
        return None

    def untileTable(self, index: int) -> QBaseTable:
        """Reset merge of the table group at index."""
        target_group = self.widget(index)
        if not isinstance(target_group, QTableGroup):
            return target_group

        current_index = self.currentIndex()
        target_group = cast(QTableGroup, target_group)
        n_merged = len(target_group.tables)
        appeared_idx: list[int] = []
        count = 0
        all_groups: list[QTableGroup] = []
        target_idx = -1
        for i in range(self.count()):
            wdt = self.widget(i)
            if target_group == wdt:
                all_groups.append(wdt)
                appeared_idx.append(i)
                if i == index:
                    target_idx = count
                count += 1

        unmerged = None
        for i, group in enumerate(all_groups):
            table = group.pop(target_idx)
            j = appeared_idx[i]
            if j == index:
                unmerged = table
                self.replaceWidget(j, table)
            elif n_merged == 2:
                self.replaceWidget(j, group.pop(0))

        if unmerged is None:
            raise RuntimeError("Unmerging could not be resolved.")
        self.setCurrentIndex(current_index)
        target_group.deleteLater()
        self.parentWidget().setCellFocus()
        return unmerged

    def copyData(self, index: int):
        """Copy all the data in the table at index to the clipboard."""
        table = self.tableAtIndex(index)
        h, w = table.dataShape()
        table.setSelections([(slice(0, h), slice(0, w))])
        table.copyToClipboard(headers=True)
        table.setSelections([])
        return None

    def openFinderDialog(self, index: int | None = None):
        """Open a dialog to find data in the table at index."""
        if index is not None:
            self.setCurrentIndex(index)
        ol = self._overlay
        ol.show()
        from ._finder import QFinderWidget

        _finder = ol.widget()
        if not isinstance(_finder, QFinderWidget):
            _finder = QFinderWidget(ol)
            _finder.searchBox().escClicked.connect(ol.hide)
            ol.addWidget(_finder)
            ol.setTitle("Find/Replace")
            _finder.searchBox().setFocus()
        return _finder

    def openFilterDialog(self, index: int | None = None):
        if index is not None:
            self.setCurrentIndex(index)
        ol = self._overlay
        ol.show()
        from ._eval import QLiteralFilterWidget

        _evaluator = QLiteralFilterWidget(ol)

        @_evaluator._line.escClicked.connect
        def _on_escape():
            ol.hide()
            self.parent().setCellFocus()

        ol.addWidget(_evaluator)
        ol.setTitle("Filter")
        _evaluator._line.setFocus()
        return _evaluator

    def openEvalDialog(self, index: int | None = None):
        if index is not None:
            self.setCurrentIndex(index)
        ol = self._overlay
        ol.show()
        from ._eval import QLiteralEvalWidget

        _evaluator = QLiteralEvalWidget(ol)

        @_evaluator._line.escClicked.connect
        def _on_escape():
            ol.hide()
            self.parent().setCellFocus()

        ol.addWidget(_evaluator)
        ol.setTitle("Evaluation")
        _evaluator._line.setFocus()
        return _evaluator

    def _group_index_to_tab_index(self, group: QTableGroup, index: int) -> int:
        # return the global in index of `index`-th table in `group`
        count = 0
        for i in range(self.count()):
            wdt = self.widget(i)
            if group == wdt:
                if count == index:
                    return i
                count += 1
        raise ValueError(f"{index} is not in {group}.")

    def _tab_index_to_group_index(self, index: int) -> int:
        wdt = cast(QTableGroup, self.widget(index))
        if isinstance(wdt, QTableGroup):
            count = 0
            for i in range(index):
                if wdt == self.widget(i):
                    count += 1
            return count
        else:
            raise ValueError(f"Widget at {index} is not a table group.")


class QEditabilityNotifier(QtW.QWidget):
    def __init__(self, table: QMutableTable, name: str) -> None:
        super().__init__()
        if len(name) > 20:
            name = name[:17] + "..."

        btn = QClickableLabel("Set editable (Ctrl+K, E)")
        btn.clicked.connect(self._on_button_clicked)
        self.setFont(QtGui.QFont("Arial"))

        _layout = QtW.QVBoxLayout()
        _layout.addWidget(QtW.QLabel(f"Table {name!r} is not editable."))
        _layout.addWidget(btn)

        self._table = weakref.ref(table)
        self.setLayout(_layout)

    def _on_button_clicked(self):
        table = self._table()
        if table is not None:
            table.setEditable(True)
            ol: QOverlayWidget = self.parentWidget()
            ol.setVisible(False)
        return None


class QLatestVersionNotifier(QtW.QWidget):
    def __init__(self, version: str):
        super().__init__()

        btn = QClickableLabel("See release note")
        btn.clicked.connect(self.open_release_note)
        self.setFont(QtGui.QFont("Arial"))

        _layout = QtW.QVBoxLayout()
        _layout.addWidget(QtW.QLabel(f"Latest version {version} is available."))
        _layout.addWidget(btn)

        self.setLayout(_layout)

    def open_release_note(self):
        """Open the release note page in the default browser."""
        from qtpy.QtGui import QDesktopServices
        from qtpy.QtCore import QUrl

        url = "https://github.com/hanjinliu/tabulous/releases"
        QDesktopServices.openUrl(QUrl(url))
        return None
