from __future__ import annotations

from typing import Callable
from functools import wraps
from pathlib import Path
import numpy as np

from tabulous import TableViewer, commands as cmds
from tabulous.widgets import TableBase

_ALL_FUNCTIONS = []
_DIR_PATH = Path(__file__).parent


def register(f: Callable[[], TableViewer | TableBase]):
    @wraps(f)
    def wrapped():
        if out := f():
            out.save_screenshot(_DIR_PATH / f"{f.__name__}.png")
            if isinstance(out, TableViewer):
                out.close()

    _ALL_FUNCTIONS.append(wrapped)
    return wrapped


def main():
    for f in _ALL_FUNCTIONS:
        f()

@register
def colormap():
    viewer = TableViewer()
    table = viewer.open_sample("iris")

    # set a continuous colormap to the "sepal_length" column
    lmin = table.data["sepal_length"].min()
    lmax = table.data["sepal_length"].max()
    lrange = lmax - lmin

    @table.text_color.set("sepal_length")
    def _(x: float):
        red = np.array([255, 0, 0, 255], dtype=np.uint8)
        blue = np.array([0, 0, 255, 255], dtype=np.uint8)
        return (x - lmin) / lrange * blue + (lmax - x) / lrange * red

    # set a discrete colormap to the "sepal_width" column
    @table.background_color.set("sepal_width")
    def _(x: float):
        return "green" if x < 3.2 else "violet"

    viewer.resize(100, 100)
    table.move_iloc(57, 2)
    return viewer

@register
def cell_labels():
    viewer = TableViewer()
    sheet = viewer.add_spreadsheet(np.arange(4))
    sheet.cell[1, 1] = "&=np.mean(df.iloc[:, 0])"
    sheet.cell.label[1, 1] = "mean: "
    viewer.native.setMinimumSize(1, 1)
    viewer.resize(120, 180)
    return sheet

@register
def tile_tables():
    viewer = TableViewer()
    sheet0 = viewer.add_spreadsheet(name="A")
    sheet0.cell[0:5, 0:5] = "A"
    sheet1 = viewer.add_spreadsheet(name="B")
    sheet1.cell[0:5, 0:5] = "B"
    viewer.tables.tile([0, 1])
    viewer.resize(100, 100)
    return viewer


if __name__ == "__main__":
    main()
