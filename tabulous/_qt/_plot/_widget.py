from __future__ import annotations

from typing import TYPE_CHECKING
import weakref
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    from matplotlib.artist import Artist

    from tabulous.widgets import TableBase


class QtMplPlotCanvas(QtW.QWidget):
    """A matplotlib figure canvas."""

    _current_widget: QtMplPlotCanvas | None = None

    def __init__(
        self,
        nrows=1,
        ncols=1,
        style=None,
        pickable: bool = True,
        table: TableBase | None = None,
    ):
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        from ._mpl_canvas import InteractiveFigureCanvas

        backend = mpl.get_backend()
        try:
            mpl.use("Agg")
            if style is None:
                fig, _ = plt.subplots(nrows, ncols, linewidth=2)
            else:
                with plt.style.context(style):
                    fig, _ = plt.subplots(nrows, ncols, linewidth=2)
        finally:
            mpl.use(backend)

        fig: Figure
        mgr = fig.canvas.manager
        canvas = InteractiveFigureCanvas(fig)
        self.canvas = canvas
        canvas.manager = mgr
        self.figure = fig

        super().__init__()
        self.setLayout(QtW.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(canvas)
        self.setMinimumWidth(180)
        self.setMinimumHeight(135)
        self.resize(180, 135)

        self._editor = QMplEditor(self)

        if pickable:
            canvas.itemDoubleClicked.connect(self._edit_artist)
            canvas.itemClicked.connect(self._item_clicked)
        canvas.clicked.connect(self._mouse_click_event)
        canvas.doubleClicked.connect(self._mouse_double_click_event)

        self._style = style
        self._table_ref = None if table is None else weakref.ref(table)
        self._selected_artist: Artist | None = None

    def get_table(self) -> TableBase | None:
        if self._table_ref is None:
            return None
        return self._table_ref()

    def cla(self) -> None:
        """Clear the current axis."""
        import matplotlib.pyplot as plt

        if self._style:
            with plt.style.context(self._style):
                self.ax.cla()
                # NOTE: for some reason, the color of the ticks and tick labels will
                # be initialized.
                color = self.ax.spines["bottom"].get_edgecolor()
                for line in self.ax.get_xticklines():
                    line.set_color(color)
                for line in self.ax.get_yticklines():
                    line.set_color(color)
                for text in self.ax.get_xticklabels():
                    text.set_color(color)
                for text in self.ax.get_yticklabels():
                    text.set_color(color)
        else:
            self.ax.cla()
        return None

    def draw(self) -> None:
        """Draw (update) the figure."""
        self.figure.tight_layout()
        self.canvas.draw()
        return None

    def _item_clicked(self, artist: Artist):
        self._selected_artist = artist

    def _repaint_ranges(self):
        table = self.get_table()
        if table is None:
            return
        table._qwidget._qtable_view._additional_ranges = []
        if hasattr(self._selected_artist, "_tabulous_ranges"):
            ranges = self._selected_artist._tabulous_ranges
            table._qwidget._qtable_view._additional_ranges.extend(ranges)
            table._qwidget._qtable_view._current_drawing_slot_ranges = []
        table.refresh()
        self._selected_artist = None

    @property
    def axes(self):
        return self.figure.axes

    @property
    def ax(self) -> Axes:
        """The first matplotlib axis."""
        try:
            _ax = self.axes[0]
        except IndexError:
            _ax = self.figure.add_subplot(111)
        return _ax

    def _reset_canvas(self, fig: Figure, draw: bool = True):
        """Create an interactive figure canvas and add it to the widget."""
        from ._mpl_canvas import InteractiveFigureCanvas

        canvas = InteractiveFigureCanvas(fig)
        self.layout().removeWidget(self.canvas)
        self.canvas = canvas
        self.layout().addWidget(canvas)
        if draw:
            self.draw()

    def _edit_artist(self, artist: Artist):
        """Open the artist editor."""
        from ._artist_editors import pick_container

        cnt = pick_container(artist)
        cnt.changed.connect(self.canvas.draw)
        self._editor.addTab(cnt.native, cnt.get_label())
        self._selected_artist = artist
        self._repaint_ranges()
        if table := self.get_table():
            self._editor.align_to_table(table)
        else:
            self._editor.align_to_table()
        return None

    @classmethod
    def current_widget(cls):
        return cls._current_widget

    def _mouse_click_event(self, event=None):
        self.__class__._current_widget = self
        self._repaint_ranges()

    def _mouse_double_click_event(self, event=None):
        self._editor.clear()
        self._editor.hide()
        self._repaint_ranges()

    def set_background_color(self, color: str):
        self.figure.set_facecolor(color)
        for ax in self.axes:
            ax.set_facecolor(color)
        self.canvas.draw()


class QMplEditor(QtW.QTabWidget):
    """Editor widget for matplotlib artists."""

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.setWindowTitle("Matplotlib Artist Editor")
        self._drag_start: QtCore.QPoint | None = None

    def addTab(self, widget: QtW.QWidget, label: str) -> int:
        """Add a tab to the editor."""
        area = QtW.QScrollArea(self)
        widget.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        out = super().addTab(area, label)
        area.setWidget(widget)
        return out

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag_start = event.pos()
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._drag_start = None
        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._drag_start is not None:
            self.move(self.mapToParent(event.pos() - self._drag_start))

        return super().mouseMoveEvent(event)

    def align_to_table(self, table: TableBase):
        """Align the editor to the table."""
        table_rect = table._qwidget._qtable_view.rect()
        topleft = table._qwidget._qtable_view.mapToGlobal(table_rect.topLeft())
        self.resize(int(table_rect.width() * 0.7), int(table_rect.height() * 0.7))
        self.move(table_rect.center() - self.rect().center() + topleft)
        return self.show()

    def align_to_screen(self):
        """Align the editor to the screen."""
        screen = QtW.QApplication.desktop().screenGeometry()
        self.resize(int(screen.width() * 0.3), int(screen.height() * 0.3))
        self.move(screen.center() - self.rect().center())
        return self.show()
