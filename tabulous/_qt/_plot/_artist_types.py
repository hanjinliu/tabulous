from __future__ import annotations
from enum import Enum


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


class HatchStyle(Enum):
    """Hatch styles."""

    diagonal = "/"
    backdiagonal = "\\"
    vertical = "|"
    horizontal = "-"
    crossed = "+"
    cross_diagonal = "x"
    small_circle = "o"
    large_circle = "O"
    dots = "."
    stars = "*"
    none = "None"
