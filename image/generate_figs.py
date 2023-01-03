from typing import Callable
from functools import wraps
from pathlib import Path
import numpy as np

from tabulous import TableViewer, commands as cmds

_ALL_FUNCTIONS = []
_DIR_PATH = Path(__file__).parent


def register(f: Callable[[], TableViewer]):
    @wraps(f)
    def wrapped():
        viewer = f()
        viewer.save_screenshot(_DIR_PATH / f"{f.__name__}.png")
        viewer.close()

    _ALL_FUNCTIONS.append(wrapped)
    return wrapped


def main():
    for f in _ALL_FUNCTIONS:
        f()


@register
def viewer_example():
    viewer = TableViewer()
    sheet = viewer.open_sample("iris", type="spreadsheet")
    grouped = viewer.add_groupby(sheet.data.groupby("species"), name="grouped")
    cmds.tab.tile_with_adjacent_table(viewer)
    grouped.move_iloc(46, 4)
    viewer.current_index = 0
    sheet.move_iloc(5, 3)
    viewer.toolbar.current_index = 5
    return viewer


@register
def filter_example():
    viewer = TableViewer()
    rng = np.random.default_rng(1234)
    sheet = viewer.add_spreadsheet(
        {"label": rng.choice(3, 50), "value": rng.normal(0, 1, 50)}
    )
    sheet.proxy.filter("label == 1")
    viewer.resize(100, 100)
    return viewer


@register
def sort_example():
    viewer = TableViewer()
    rng = np.random.default_rng(1234)
    sheet = viewer.add_spreadsheet(
        {
            "label": rng.choice(["Alice", "Bob", "Charlie"], 12),
            "value": rng.poisson(3.5, size=12),
        }
    )
    sheet.proxy.sort(by=["label", "value"])
    viewer.resize(100, 100)
    return viewer


@register
def colormap_example():
    viewer = TableViewer()
    sheet = viewer.open_sample("iris", type="spreadsheet")
    sheet.background_colormap(
        "species",
        {"setosa": "lightblue", "versicolor": "orange", "virginica": "violet"},
    )

    @sheet.foreground_colormap("petal_width")
    def _cmap(v):
        v = float(v)
        r = (v - 0.1) / 2.4 * 255
        b = (1 - (v - 0.1) / 2.4) * 255
        return [r, 255, b, 255]

    viewer.resize(100, 100)
    sheet.move_iloc(53, 4)
    sheet.move_iloc(49, 3)
    return viewer


@register
def eval_example():
    viewer = TableViewer()
    sheet = viewer.add_spreadsheet(np.arange(100))
    sheet.cell[0, 2] = "0.20"
    sheet.cell.label[0, 2] = "freq:"
    sheet.cell[0, 1] = "&=np.sin(df.iloc[:, 0] * df.iloc[0, 2])"
    df = sheet.data
    sheet.plt.plot(df.iloc[:, 0], df.iloc[:, 1])
    viewer.resize(100, 100)
    sheet.move_iloc(3, 1)
    return viewer


@register
def command_palette_example():
    viewer = TableViewer()
    viewer.add_spreadsheet()
    viewer.resize(100, 100)
    cmds.window.show_command_palette(viewer)
    return viewer


if __name__ == "__main__":
    main()
