from __future__ import annotations
from enum import Enum
import weakref
from matplotlib.collections import PathCollection, LineCollection
from matplotlib.container import BarContainer
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.patches import Patch

from matplotlib.artist import Artist

from magicgui.widgets import ComboBox, Container, SpinBox, FloatSpinBox, Widget


class Marker(Enum):
    """Marker shapes."""

    point = "."
    pixel = ","
    circle = "o"
    triangle_down = "v"
    triangle_up = "^"
    triangle_left = "<"
    triangle_right = ">"
    tri_down = "1"
    tri_up = "2"
    tri_left = "3"
    tri_right = "4"
    octagon = "8"
    square = "s"
    pentagon = "p"
    star = "*"
    hexagon1 = "h"
    hexagon2 = "H"
    plus = "+"
    x = "x"
    diamond = "D"
    thin_diamond = "d"
    vline = "|"
    hline = "-"
    none = "None"


class LineStyle(Enum):
    """Line styles."""

    solid = "-"
    dashed = "--"
    dotted = ":"
    dash_dot = "-."
    none = "None"


class Line2DEdit(Container):
    def __init__(self, line: Line2D) -> None:
        from .._color_edit import ColorEdit

        self._line = weakref.ref(line)
        widgets = []

        # line color
        color = line.get_color()
        if not isinstance(color, str):
            color = [int(c * 255) for c in color]
        _color_edit = ColorEdit(name="color", value=color)
        _color_edit.changed.connect(self.set_color)
        widgets.append(_color_edit)

        # line style
        _ls_edit = ComboBox(
            choices=LineStyle, value=LineStyle(line.get_linestyle()), label="linestyle"
        )
        _ls_edit.changed.connect(self.set_linestyle)
        widgets.append(_ls_edit)

        # line width
        _lw_edit = FloatSpinBox(
            min=0.0, max=10.0, step=0.5, value=line.get_linewidth(), label="linewidth"
        )
        _lw_edit.changed.connect(self.set_linewidth)
        widgets.append(_lw_edit)

        _marker = ComboBox(
            choices=Marker, label="marker", value=Marker(line.get_marker())
        )
        _marker.changed.connect(self.set_marker)
        _markerfacecolor = ColorEdit(
            label="marker face color", value=fix_color(line.get_markerfacecolor())
        )
        _markerfacecolor.changed.connect(self.set_markerfacecolor)
        _markeredgecolor = ColorEdit(
            label="marker edge color", value=fix_color(line.get_markeredgecolor())
        )
        _markeredgecolor.changed.connect(self.set_markeredgecolor)
        _markeredgewidth = FloatSpinBox(
            min=0.0,
            max=10.0,
            step=0.5,
            label="marker edge width",
            value=line.get_markeredgewidth(),
        )
        _markeredgewidth.changed.connect(self.set_markeredgewidth)
        _markersize = FloatSpinBox(
            label="marker size",
            min=0.0,
            max=50.0,
            step=0.5,
            value=line.get_markersize(),
        )
        _markersize.changed.connect(self.set_markersize)

        self._marker_related: list[Widget] = [
            _markerfacecolor,
            _markeredgecolor,
            _markeredgewidth,
            _markersize,
        ]

        widgets.extend(
            [_marker, _markerfacecolor, _markeredgecolor, _markeredgewidth, _markersize]
        )

        # zorder
        _zorder = SpinBox(min=-10000, max=10000, value=line.get_zorder(), name="zorder")
        _zorder.changed.connect(self.set_zorder)
        widgets.append(_zorder)

        super().__init__(widgets=widgets)
        self.set_marker(_marker.value)

    @property
    def line(self) -> Line2D:
        """Return the Line2D object."""
        out = self._line()
        if out is None:
            raise ValueError("Line2D object has been deleted.")
        return out

    def set_color(self, rgba: tuple[int, int, int, int]) -> None:
        """Set the line color."""
        self.line.set_color([a / 255 for a in rgba])

    def set_linestyle(self, ls: LineStyle):
        self.line.set_linestyle(ls.value)

    def set_linewidth(self, lw: float):
        self.line.set_linewidth(lw)

    def set_zorder(self, zorder: int):
        self.line.set_zorder(zorder)

    def set_marker(self, marker: Marker):
        marker = Marker(marker)
        self.line.set_marker(marker.value)
        has_marker = marker != Marker.none
        for wdt in self._marker_related:
            wdt.enabled = has_marker

    def set_markerfacecolor(self, rgba):
        self.line.set_markerfacecolor([a / 255 for a in rgba])

    def set_markeredgecolor(self, rgba):
        self.line.set_markeredgecolor([a / 255 for a in rgba])

    def set_markeredgewidth(self, width: float):
        self.line.set_markeredgewidth(width)

    def set_markersize(self, size: float):
        self.line.set_markersize(size)


class ScatterEdit(Container):
    def __init__(self, scatter: PathCollection) -> None:
        from .._color_edit import ColorEdit

        self._line = weakref.ref(scatter)

        # scatter color
        _facecolor = ColorEdit(
            name="face color", value=scatter.get_facecolor()[0] * 255
        )
        _facecolor.changed.connect(self.set_facecolor)

        _edgecolor = ColorEdit(
            name="edge color", value=scatter.get_edgecolor()[0] * 255
        )
        _edgecolor.changed.connect(self.set_edgecolor)

        # _edgewidth = FloatSpinBox(name="edge width", value=scatter.get_linewidth())

        # marker
        # _marker_edit = ComboBox(choices=Marker, value=line.get_marker(), name="marker")
        # _marker_edit.changed.connect(self.set_marker)

        _size_edit = FloatSpinBox(
            min=0.0, max=500.0, step=0.5, value=scatter.get_sizes()[0], name="size"
        )
        _size_edit.changed.connect(self.set_size)

        # zorder
        _zorder = SpinBox(
            min=-10000, max=10000, value=scatter.get_zorder(), name="zorder"
        )
        _zorder.changed.connect(self.set_zorder)

        super().__init__(widgets=[_facecolor, _edgecolor, _size_edit, _zorder])

    @property
    def scatter(self) -> PathCollection:
        """Return the Line2D object."""
        out = self._line()
        if out is None:
            raise ValueError("PathCollection object has been deleted.")
        return out

    def set_facecolor(self, rgba: tuple[int, int, int, int]) -> None:
        """Set face colors of the scatter."""
        self.scatter.set_facecolor([a / 255 for a in rgba])

    def set_edgecolor(self, rgba: tuple[int, int, int, int]) -> None:
        """Set edge colors of the scatter."""
        self.scatter.set_edgecolors([a / 255 for a in rgba])

    # def set_marker(self, marker: str):
    #     self.line.set_marker(marker)

    def set_size(self, size: int) -> None:
        self.scatter.set_sizes([size])

    def set_zorder(self, zorder: int):
        self.scatter.set_zorder(zorder)


class RContainerEdit(Container):
    def __init__(self, artist: BarContainer):
        from .._color_edit import ColorEdit

        self._obj = weakref.ref(artist)

        line = self.artist

        _color = ColorEdit(name="color", value=fix_color(line.get_color()[0]))
        _color.changed.connect(self.set_facecolor)

    @property
    def artist(self) -> BarContainer:
        out = self._obj()
        if out is None:
            raise ValueError("LineCollection object has been deleted.")
        return out

    def set_facecolor(self, color):
        ...


class LineCollectionEdit(Container):
    def __init__(self, lines: LineCollection):
        from .._color_edit import ColorEdit

        self._obj = weakref.ref(lines)

        line = self.lines

        _color = ColorEdit(name="color", value=fix_color(line.get_color()[0]))
        _color.changed.connect(self.set_errorbar_color)

        # line width
        _lw_edit = FloatSpinBox(
            min=0.0, max=10.0, step=0.5, value=line.get_linewidth(), name="linewidth"
        )
        _lw_edit.changed.connect(self.set_linewidth)

    @property
    def lines(self) -> LineCollection:
        out = self._obj()
        if out is None:
            raise ValueError("LineCollection object has been deleted.")
        return out

    def set_errorbar_color(self, rgba):
        self.lines.set_color([a / 255 for a in rgba])

    def set_linewidth(self, width: float):
        self.lines.set_linewidth(width)


def pick_container(artist: Artist) -> Container:
    """Return a proper container for the given artist."""
    if isinstance(artist, Line2D):
        return Line2DEdit(artist)
    elif isinstance(artist, PathCollection):
        return ScatterEdit(artist)
    elif isinstance(artist, LineCollection):
        return LineCollectionEdit(artist)
    raise ValueError(f"No container found for artist {type(artist).__name__}.")


def fix_color(color):
    if not isinstance(color, str):
        color = [int(c * 255) for c in color]
    return color
