from __future__ import annotations
from functools import wraps
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
import matplotlib as mpl
import matplotlib.pyplot as plt
from ._mpl_canvas import InteractiveFigureCanvas

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    from matplotlib.lines import Line2D
    from matplotlib.collections import PathCollection
    from matplotlib.text import Text
    from matplotlib.quiver import Quiver
    from matplotlib.legend import Legend

    import seaborn as sns
    from seaborn.axisgrid import Grid


class QPlotCanvas(QtW.QWidget):
    """A matplotlib figure canvas."""

    def __init__(
        self,
        nrows=1,
        ncols=1,
        figsize=(4.0, 3.0),
        style=None,
    ):
        backend = mpl.get_backend()
        try:
            mpl.use("Agg")
            if style is None:
                fig, _ = plt.subplots(nrows, ncols, figsize=figsize)
            else:
                with plt.style.context(style):
                    fig, _ = plt.subplots(nrows, ncols, figsize=figsize)
        finally:
            mpl.use(backend)

        fig: Figure
        canvas = InteractiveFigureCanvas(fig)
        self.canvas = canvas
        self.figure = fig

        super().__init__()
        self.setLayout(QtW.QVBoxLayout())
        self.layout().addWidget(canvas)
        self.setMinimumWidth(40)
        self.setMinimumHeight(40)

    def draw(self):
        self.figure.tight_layout()
        self.canvas.draw()

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


def _use_seaborn_grid(f):
    """
    Some seaborn plot functions will create a new figure.
    This decorator provides a common way to update figure canvas in the widget.
    """

    @wraps(f)
    def func(self: QPlotCanvas, *args, **kwargs):
        backend = mpl.get_backend()
        try:
            mpl.use("Agg")
            grid: Grid = f(self, *args, **kwargs)
        finally:
            mpl.use(backend)

        self._reset_canvas(grid.figure)
        return grid

    return func