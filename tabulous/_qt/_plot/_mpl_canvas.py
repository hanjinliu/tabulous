from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from matplotlib.backend_bases import MouseEvent, MouseButton

from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Signal

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    from matplotlib.legend import Legend

    class FigureCanvas(QtW.QWidget):
        ...

else:
    from matplotlib.backends.backend_qt5agg import FigureCanvas


class InteractiveFigureCanvas(FigureCanvas):
    """A figure canvas implemented with mouse callbacks."""

    figure: Figure
    deleteRequested = Signal()
    itemClicked = Signal(object)
    itemDoubleClicked = Signal(object)
    clicked = Signal(object)
    doubleClicked = Signal()  # emitted *before* itemPicked event

    def __init__(self, fig):
        super().__init__(fig)
        self.pressed = None
        self.lastx_pressed = None
        self.lasty_pressed = None
        self.lastx = None
        self.lasty = None
        self.last_axis: Axes | None = None
        self._interactive = True
        fig.canvas.mpl_connect("pick_event", self._emit_pick_event)

    def _emit_pick_event(self, event):
        ax: Axes = event.mouseevent.inaxes
        if ax:
            artist = event.artist
            if ax.containers:
                for container in ax.containers:
                    # if an artist is in a container, emit the container instead
                    if artist in container:
                        artist = container
                        break
            if event.mouseevent.dblclick:
                self.itemDoubleClicked.emit(artist)
            else:
                self.itemClicked.emit(artist)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        """
        Resize figure by changing axes xlim and ylim. If there are subplots,
        only the subplot in which cursor exists will be resized.
        """
        ax = self.last_axis
        if not self._interactive or not ax:
            return
        delta = event.angleDelta().y() / 120
        event = self.get_mouse_event(event)
        factor = 0.75**delta

        _zoom_x_wheel(ax, factor)
        _zoom_y_wheel(ax, factor)
        self.figure.canvas.draw()
        return None

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Record the starting coordinates of mouse drag."""
        mouse_event = self.get_mouse_event(event)
        self.lastx_pressed = self.lastx = mouse_event.xdata
        self.lasty_pressed = self.lasty = mouse_event.ydata
        if mouse_event.inaxes:
            self.pressed = mouse_event.button
            self.last_axis = mouse_event.inaxes
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Translate axes focus while dragging. If there are subplots, only the
        subplot in which cursor exists will be translated.
        """
        ax = self.last_axis
        if (
            self.pressed not in (MouseButton.LEFT, MouseButton.RIGHT)
            or self.lastx_pressed is None
            or not self._interactive
            or not ax
        ):
            return None

        event = self.get_mouse_event(event)
        x, y = event.xdata, event.ydata

        if x is None or y is None:
            return None

        if self.pressed == MouseButton.LEFT:
            _translate_x(ax, self.lastx_pressed, x)
            _translate_y(ax, self.lasty_pressed, y)
        elif self.pressed == MouseButton.RIGHT:
            _zoom_x(ax, self.lastx, x)
            _zoom_y(ax, self.lasty, y)

        self.lastx, self.lasty = x, y
        self.figure.canvas.draw()
        return None

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Stop dragging state."""
        pos = event.pos()
        mouse_event = self.get_mouse_event(event)

        if self.lastx == mouse_event.xdata and self.lasty == mouse_event.ydata:
            # clicked, not dragged
            if self.pressed == MouseButton.LEFT:
                self.clicked.emit(mouse_event)

            elif self.pressed == MouseButton.RIGHT:
                menu = self._make_context_menu(mouse_event)
                menu.exec_(self.mapToGlobal(pos))

        self.pressed = None

        return super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        """Adjust layout upon dougle click."""
        if not self._interactive:
            return

        self.doubleClicked.emit()
        x, y = self.mouseEventCoords(event.pos())
        button = self.buttond.get(event.button())

        if button is not None:
            # native button press event to pick artists
            self.button_press_event(x, y, button, guiEvent=event)

        self.figure.tight_layout()
        self.figure.canvas.draw()
        return super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event):
        """Adjust layout upon canvas resized."""
        super().resizeEvent(event)
        self.figure.tight_layout()
        self.figure.canvas.draw()
        return None

    def get_mouse_event(self, event, name="") -> MouseEvent:
        x, y = self.mouseEventCoords(event)
        if hasattr(event, "button"):
            button = self.buttond.get(event.button())
        else:
            button = None
        mouse_event = MouseEvent(name, self, x, y, button=button, guiEvent=event)
        return mouse_event

    def _make_context_menu(self, event: MouseEvent) -> QtW.QMenu:
        """Make a QMenu object with default actions."""
        menu = QtW.QMenu(self)
        menu.addAction("Copy ...", self._copy_canvas)
        menu.addAction("Save As...", self._save_canvas_dialog)
        menu.addAction("Clear figure", self._clear_figure)
        menu.addAction("Legend", self._toggle_legend)
        menu.addSeparator()
        return menu

    def _save_canvas_dialog(self, format="PNG"):
        """Open a file dialog and save the current canvas state."""
        dialog = QtW.QFileDialog(self, "Save Image")
        dialog.setAcceptMode(QtW.QFileDialog.AcceptMode.AcceptSave)
        dialog.setDefaultSuffix(format.lower())
        dialog.setNameFilter(f"{format} file (*.{format.lower()})")
        if dialog.exec_():
            filename = dialog.selectedFiles()[0]
            self.figure.savefig(filename)

    def _clear_figure(self):
        for ax in self.figure.axes:
            ax.cla()
        self.figure.canvas.draw()

    def _toggle_legend(self):
        legend: Legend = self.last_axis.get_legend()
        if legend is None:
            self.last_axis.legend()
        else:
            legend.set_visible(not legend.get_visible())
        self.figure.canvas.draw()

    def _asarray(self) -> np.ndarray:
        """Convert current canvas state into RGBA numpy array."""
        return np.asarray(self.renderer.buffer_rgba(), dtype=np.uint8)

    def _copy_canvas(self):
        """Copy current canvas state into clipboard."""
        arr = self._asarray()
        clipboard = QtW.QApplication.clipboard()
        h, w, _ = arr.shape
        image = QtGui.QImage(arr, w, h, QtGui.QImage.Format.Format_RGBA8888)
        clipboard.setImage(image)


def _translate_x(ax: Axes, xstart: float, xstop: float):
    xscale = ax.get_xscale()
    x0, x1 = ax.get_xlim()
    if xscale == "linear":
        dx = xstop - xstart
        ax.set_xlim([x0 - dx, x1 - dx])
    elif xscale == "log":
        if xstart <= 0 or xstop <= 0:
            ax.autoscale(axis="x")
        else:
            ratio = xstart / xstop
            ax.set_xlim([x0 * ratio, x1 * ratio])


def _translate_y(ax: Axes, ystart: float, ystop: float):
    yscale = ax.get_yscale()
    y0, y1 = ax.get_ylim()
    if yscale == "linear":
        dy = ystop - ystart
        ax.set_ylim([y0 - dy, y1 - dy])
    elif yscale == "log":
        if ystart <= 0 or ystop <= 0:
            ax.autoscale(axis="y")
        else:
            ratio = ystart / ystop
            ax.set_ylim([y0 * ratio, y1 * ratio])


def _zoom_x(ax: Axes, xstart: float, xstop: float):
    xscale = ax.get_xscale()
    x0, x1 = ax.get_xlim()
    if xscale == "linear":
        _u = x1 + x0
        _v = x1 - x0
        dx = xstop - xstart
        ax.set_xlim([_u / 2 - _v / 2 + dx, _u / 2 + _v / 2 - dx])
    elif xscale == "log":
        if xstart <= 0 or xstop <= 0:
            ax.autoscale(axis="x")
        ratio = xstop / xstart
        ax.set_xlim([x0 * ratio, x1 / ratio])


def _zoom_y(ax: Axes, ystart: float, ystop: float):
    yscale = ax.get_yscale()
    y0, y1 = ax.get_ylim()
    if yscale == "linear":
        _u = y1 + y0
        _v = y1 - y0
        dy = ystop - ystart
        ax.set_ylim([_u / 2 - _v / 2 + dy, _u / 2 + _v / 2 - dy])
    elif yscale == "log":
        if ystart <= 0 or ystop <= 0:
            ax.autoscale(axis="y")
        else:
            ratio = ystop / ystart
            ax.set_ylim([y0 * ratio, y1 / ratio])


def _zoom_x_wheel(ax: Axes, factor: float):
    xscale = ax.get_xscale()
    x0, x1 = ax.get_xlim()
    if xscale == "linear":
        _u = x1 + x0
        _v = x1 - x0
        ax.set_xlim([_u / 2 - _v / 2 * factor, _u / 2 + _v / 2 * factor])
    elif xscale == "log":
        if x0 <= 0 or x1 <= 0:
            ax.autoscale(axis="x")
        else:
            xc = (x0 * x1) ** 0.5
            x0_t = (x0 / xc) ** factor
            x1_t = (x1 / xc) ** factor
            ax.set_xlim([x0_t * xc, x1_t * xc])


def _zoom_y_wheel(ax: Axes, factor: float):
    yscale = ax.get_yscale()
    y0, y1 = ax.get_ylim()
    if yscale == "linear":
        _u = y1 + y0
        _v = y1 - y0
        ax.set_ylim([_u / 2 - _v / 2 * factor, _u / 2 + _v / 2 * factor])
    elif yscale == "log":
        if y0 <= 0 or y1 <= 0:
            ax.autoscale(axis="y")
        else:
            yc = (y0 * y1) ** 0.5
            y0_t = (y0 / yc) ** factor
            y1_t = (y1 / yc) ** factor
            ax.set_ylim([y0_t * yc, y1_t * yc])
