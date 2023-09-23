from __future__ import annotations

from qtpy.sip import isdeleted
from ._base import TableComponent


def _plt_function(name: str, method_name: str | None = None):
    """Make a function that calls ``plt.<name>`` on the current figure."""
    if method_name is None:
        method_name = name

    def func(self: PlotInterface, *args, **kwargs):
        ax = self.gca()
        out = getattr(ax, method_name)(*args, picker=True, **kwargs)
        self.draw()
        return out

    func.__name__ = name
    func.__qualname__ = f"PlotInterface.{name}"
    func.__doc__ = f"Call ``plt.{name}`` on the current figure."
    return func


class PlotInterface(TableComponent):
    """The interface of plotting."""

    def __init__(self, parent=TableComponent._no_ref):
        super().__init__(parent)
        self._current_widget = None

    def gcf(self):
        """Get current figure."""
        return self.gcw().figure

    def gca(self):
        """Get current axis."""
        return self.gcw().ax

    def gcw(self):
        """Get current widget."""
        if self._current_widget is None or isdeleted(self._current_widget):
            self.new_widget()
        return self._current_widget

    def clf(self):
        """Clear the current figure."""
        self.gcf().clf()
        return self.draw()

    def cla(self):
        """Clear the current axis."""
        self.gca().cla()
        return self.draw()

    def new_widget(self, nrows: int = 1, ncols: int = 1, style: str | None = None):
        """Create a new plot widget and add it to the table."""
        from tabulous._qt._plot import QtMplPlotCanvas

        table = self.parent
        qviewer = table._qwidget._qtable_view.parentViewer()

        if not qviewer._white_background and style is None:
            style = "dark_background"

        wdt = QtMplPlotCanvas(nrows=nrows, ncols=ncols, style=style, table=table)
        wdt.set_background_color(qviewer.backgroundColor().name())
        wdt.canvas.deleteRequested.connect(self.delete_widget)
        table.add_side_widget(wdt, name="Plot")
        self._current_widget = wdt
        return wdt

    def delete_widget(self) -> None:
        """Delete the current widget from the side area."""
        if self._current_widget is None:
            return None
        try:
            self.parent._qwidget._side_area.removeWidget(self._current_widget)
        except Exception:
            pass
        self._current_widget.deleteLater()
        self._current_widget = None
        return None

    def figure(self, style=None):
        return self.subplots(style=style)[0]

    def subplots(self, nrows=1, ncols=1, style=None):
        wdt = self.new_widget(nrows=nrows, ncols=ncols, style=style)
        return wdt.figure, wdt.axes

    plot = _plt_function("plot")
    plot_date = _plt_function("plot_date")
    quiver = _plt_function("quiver")
    scatter = _plt_function("scatter")
    bar = _plt_function("bar")
    errorbar = _plt_function("errorbar")
    hist = _plt_function("hist")
    text = _plt_function("text")
    fill_between = _plt_function("fill_between")
    fill_betweenx = _plt_function("fill_betweenx")

    def xlabel(self, *args, **kwargs):
        """Call ``plt.xlabel`` on the current side figure."""
        if not args and not kwargs:
            return self.gca().get_xlabel()
        out = self.gca().set_xlabel(*args, **kwargs)
        self.draw()
        return out

    def ylabel(self, *args, **kwargs):
        """Call ``plt.ylabel`` on the current side figure."""
        if not args and not kwargs:
            return self.gca().get_ylabel()
        out = self.gca().set_ylabel(*args, **kwargs)
        self.draw()
        return out

    def xlim(self, *args, **kwargs):
        """Call ``plt.xlim`` on the current side figure."""
        if not args and not kwargs:
            return self.gca().get_xlim()
        out = self.gca().set_xlim(*args, **kwargs)
        self.draw()
        return out

    def ylim(self, *args, **kwargs):
        """Call ``plt.ylim`` on the current side figure."""
        if not args and not kwargs:
            return self.gca().get_ylim()
        out = self.gca().set_ylim(*args, **kwargs)
        self.draw()
        return out

    def title(self, *args, **kwargs):
        """Call ``plt.title`` on the current side figure."""
        if not args and not kwargs:
            return self.gca().get_title()
        out = self.gca().set_title(*args, **kwargs)
        self.draw()
        return out

    def draw(self):
        """Update the current side figure."""
        return self._current_widget.draw()

    @property
    def background_color(self):
        """Background color of the current figure."""
        return self.gcf().get_facecolor()

    @background_color.setter
    def background_color(self, color):
        """Set background color of the current figure."""
        return self.gcw().set_background_color(color)
