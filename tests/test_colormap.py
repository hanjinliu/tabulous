from tabulous import TableViewer
from qtpy.QtGui import QColor
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

    table.foreground_colormap("char", cmap)
    assert _utils.get_cell_foreground_color(table.native, 0, 0) == QColor(*cmap["a"])
    assert _utils.get_cell_foreground_color(table.native, 1, 0) == QColor(*cmap["b"])
    assert _utils.get_cell_foreground_color(table.native, 2, 0) == QColor(*cmap["c"])

    table.foreground_colormap("char", None)
    assert _utils.get_cell_foreground_color(table.native, 0, 0) == default_color
    assert _utils.get_cell_foreground_color(table.native, 1, 0) == default_color
    assert _utils.get_cell_foreground_color(table.native, 2, 0) == default_color

    table.foreground_colormap("char", _cmap_func)
    assert _utils.get_cell_foreground_color(table.native, 0, 0) == QColor(*cmap["a"])
    assert _utils.get_cell_foreground_color(table.native, 1, 0) == QColor(*cmap["b"])
    assert _utils.get_cell_foreground_color(table.native, 2, 0) == QColor(*cmap["c"])


def test_background():
    viewer = TableViewer(show=False)
    table = viewer.add_table({"char": ["a", "b", "c"]})
    default_color = _utils.get_cell_background_color(table.native, 0, 0)

    table.background_colormap("char", cmap)
    assert _utils.get_cell_background_color(table.native, 0, 0) == QColor(*cmap["a"])
    assert _utils.get_cell_background_color(table.native, 1, 0) == QColor(*cmap["b"])
    assert _utils.get_cell_background_color(table.native, 2, 0) == QColor(*cmap["c"])

    table.background_colormap("char", None)
    assert _utils.get_cell_background_color(table.native, 0, 0) == default_color
    assert _utils.get_cell_background_color(table.native, 1, 0) == default_color
    assert _utils.get_cell_background_color(table.native, 2, 0) == default_color

    table.background_colormap("char", _cmap_func)
    assert _utils.get_cell_background_color(table.native, 0, 0) == QColor(*cmap["a"])
    assert _utils.get_cell_background_color(table.native, 1, 0) == QColor(*cmap["b"])
    assert _utils.get_cell_background_color(table.native, 2, 0) == QColor(*cmap["c"])
