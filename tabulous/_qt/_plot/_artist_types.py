from __future__ import annotations
from enum import Enum
import weakref
from matplotlib.collections import PathCollection
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.patches import Patch

from matplotlib.artist import Artist

from magicgui.widgets import ComboBox, Container, FloatSpinBox


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

        # line color
        _color_edit = ColorEdit(name="color", value=line.get_color())
        _color_edit.changed.connect(self.set_color)

        # line style
        _ls_edit = ComboBox(
            choices=LineStyle, value=LineStyle(line.get_linestyle()), name="linestyle"
        )
        _ls_edit.changed.connect(self.set_linestyle)

        # line width
        _lw_edit = FloatSpinBox(
            min=0.0, max=10.0, step=0.5, value=line.get_linewidth(), name="linewidth"
        )
        _lw_edit.changed.connect(self.set_linewidth)

        super().__init__(widgets=[_color_edit, _ls_edit, _lw_edit])

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


class ScatterEdit(Container):
    def __init__(self, scatter: PathCollection) -> None:
        from .._color_edit import ColorEdit

        self._line = weakref.ref(scatter)

        # scatter color
        _facecolor = ColorEdit(name="color", value=scatter.get_facecolor()[0] * 255)
        _facecolor.changed.connect(self.set_facecolor)

        _edgecolor = ColorEdit(name="edgecolor", value=scatter.get_edgecolor()[0] * 255)
        _edgecolor.changed.connect(self.set_edgecolor)

        # marker
        # _marker_edit = ComboBox(choices=Marker, value=line.get_marker(), name="marker")
        # _marker_edit.changed.connect(self.set_marker)

        _size_edit = FloatSpinBox(
            min=0.0, max=500.0, step=0.5, value=scatter.get_sizes()[0], name="size"
        )
        _size_edit.changed.connect(self.set_size)
        super().__init__(widgets=[_facecolor, _edgecolor, _size_edit])

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


def pick_container(artist: Artist) -> Container:
    """Return a proper container for the given artist."""
    if isinstance(artist, Line2D):
        return Line2DEdit(artist)
    elif isinstance(artist, PathCollection):
        return ScatterEdit(artist)
    raise ValueError("No Line2DEdit container found for artist.")
