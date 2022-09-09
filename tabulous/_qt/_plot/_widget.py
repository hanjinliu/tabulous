from __future__ import annotations
from functools import wraps
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW

try:
    import matplotlib as mpl
except ImportError as e:
    raise ImportError(
        "Module 'matplotlib' is not installed. Please install it to use plot canvas."
    )
import matplotlib.pyplot as plt
from ._mpl_canvas import InteractiveFigureCanvas

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    from matplotlib.artist import Artist

    import seaborn as sns
    from seaborn.axisgrid import Grid


class QtMplPlotCanvas(QtW.QWidget):
    """A matplotlib figure canvas."""

    def __init__(
        self,
        nrows=1,
        ncols=1,
        style=None,
    ):
        backend = mpl.get_backend()
        try:
            mpl.use("Agg")
            if style is None:
                fig, _ = plt.subplots(nrows, ncols)
            else:
                with plt.style.context(style):
                    fig, _ = plt.subplots(nrows, ncols)
        finally:
            mpl.use(backend)

        fig: Figure
        canvas = InteractiveFigureCanvas(fig)
        self.canvas = canvas
        self.figure = fig

        super().__init__()
        self.setLayout(QtW.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(canvas)
        self.setMinimumWidth(180)
        self.setMinimumHeight(135)
        self.resize(180, 135)

        self._editor = QMplEditor()
        self._editor.setParent(self, self._editor.windowFlags())

        canvas.itemPicked.connect(self._edit_artist)
        canvas.doubleClicked.connect(self._editor.clear)

    def cla(self) -> None:
        """Clear the current axis."""
        self.ax.cla()
        return None

    def draw(self) -> None:
        """Draw (update) the figure."""
        self.figure.tight_layout()
        self.canvas.draw()
        return None

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
        from ._artist_editors import pick_container

        cnt = pick_container(artist)
        cnt.changed.connect(self.canvas.draw)
        self._editor.addTab(cnt.native, cnt.get_label())
        self._editor.show()
        return None


def _use_seaborn_grid(f):
    """
    Some seaborn plot functions will create a new figure.
    This decorator provides a common way to update figure canvas in the widget.
    """

    @wraps(f)
    def func(self: QtMplPlotCanvas, *args, **kwargs):
        backend = mpl.get_backend()
        try:
            mpl.use("Agg")
            grid: Grid = f(self, *args, **kwargs)
        finally:
            mpl.use(backend)

        self._reset_canvas(grid.figure)
        return grid

    return func


class QMplEditor(QtW.QTabWidget):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Matplotlib Artist Editor")

    def addTab(self, widget: QtW.QWidget, label: str) -> int:
        """Add a tab to the editor."""
        area = QtW.QScrollArea(self)
        widget.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        out = super().addTab(area, label)
        area.setWidget(widget)
        return out
