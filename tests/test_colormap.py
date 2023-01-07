from tabulous import TableViewer
from tabulous.widgets import Table
from tabulous.color import normalize_color
from qtpy.QtGui import QColor
import numpy as np
from . import _utils

cmap = {
    "a": [255, 0, 0, 255],
    "b": [0, 255, 0, 255],
    "c": [0, 0, 255, 255],
}

def _cmap_func(x):
    return cmap[x]

def test_foreground():
    viewer = TableViewer(show=False)
    table = viewer.add_table({"char": ["a", "b", "c"]})
    default_color = _utils.get_cell_foreground_color(table.native, 0, 0)

    table.text_color.set("char", cmap)
    assert _utils.get_cell_foreground_color(table.native, 0, 0) == QColor(*cmap["a"])
    assert _utils.get_cell_foreground_color(table.native, 1, 0) == QColor(*cmap["b"])
    assert _utils.get_cell_foreground_color(table.native, 2, 0) == QColor(*cmap["c"])

    table.text_color.set("char", None)
    assert _utils.get_cell_foreground_color(table.native, 0, 0) == default_color
    assert _utils.get_cell_foreground_color(table.native, 1, 0) == default_color
    assert _utils.get_cell_foreground_color(table.native, 2, 0) == default_color

    table.text_color.set("char", _cmap_func)
    assert _utils.get_cell_foreground_color(table.native, 0, 0) == QColor(*cmap["a"])
    assert _utils.get_cell_foreground_color(table.native, 1, 0) == QColor(*cmap["b"])
    assert _utils.get_cell_foreground_color(table.native, 2, 0) == QColor(*cmap["c"])


def test_background():
    viewer = TableViewer(show=False)
    table = viewer.add_table({"char": ["a", "b", "c"]})
    default_color = _utils.get_cell_background_color(table.native, 0, 0)

    table.background_color.set("char", cmap)
    assert _utils.get_cell_background_color(table.native, 0, 0) == QColor(*cmap["a"])
    assert _utils.get_cell_background_color(table.native, 1, 0) == QColor(*cmap["b"])
    assert _utils.get_cell_background_color(table.native, 2, 0) == QColor(*cmap["c"])

    table.background_color.set("char", None)
    assert _utils.get_cell_background_color(table.native, 0, 0) == default_color
    assert _utils.get_cell_background_color(table.native, 1, 0) == default_color
    assert _utils.get_cell_background_color(table.native, 2, 0) == default_color

    table.background_color.set("char", _cmap_func)
    assert _utils.get_cell_background_color(table.native, 0, 0) == QColor(*cmap["a"])
    assert _utils.get_cell_background_color(table.native, 1, 0) == QColor(*cmap["b"])
    assert _utils.get_cell_background_color(table.native, 2, 0) == QColor(*cmap["c"])

def test_linear_interpolation():
    table = Table({"A": np.arange(10)})
    table.text_color.set("A", interp_from=["red", "blue"])
    assert table.cell.text_color[0, 0] == normalize_color("red")
    assert table.cell.text_color[9, 0] == normalize_color("blue")

def test_invert():
    table = Table({"A": np.arange(10)})
    table.text_color.set("A", interp_from=["red", "blue"])
    red = normalize_color("red")
    red_inv = tuple(255 - x for x in red[:3]) + (red[3],)

    assert table.cell.text_color[0, 0] == red
    table.text_color.invert("A")
    assert table.cell.text_color[0, 0] == red_inv

def test_set_opacity():
    table = Table({"A": np.arange(10)})
    table.text_color.set("A", interp_from=["red", "blue"])
    assert table.cell.text_color[0, 0][3] == 255

    table.text_color.set_opacity("A", 0.5)
    assert table.cell.text_color[0, 0][3] == 127

    table.text_color.set("A", interp_from=["red", "blue"], opacity=0.5)
    assert table.cell.text_color[0, 0][3] == 127
