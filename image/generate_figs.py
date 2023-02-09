from pathlib import Path
import numpy as np
from magicgui import magicgui
from magicgui.widgets import TextEdit

from tabulous import TableViewer, commands as cmds

from tabulous_doc import FunctionRegistry

REG = FunctionRegistry(Path(__file__).parent)


@REG.register
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


@REG.register
def filter_example():
    viewer = TableViewer()
    rng = np.random.default_rng(1234)
    sheet = viewer.add_spreadsheet(
        {"label": rng.choice(3, 50), "value": rng.normal(0, 1, 50)}
    )
    sheet.proxy.filter("label == 1")
    viewer.size = (100, 100)
    return viewer


@REG.register
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
    viewer.size = (100, 100)
    return viewer


@REG.register
def colormap_example():
    viewer = TableViewer()
    sheet = viewer.open_sample("iris", type="spreadsheet")
    sheet["species"].background_color.set(
        {"setosa": "lightblue", "versicolor": "orange", "virginica": "violet"},
    )
    sheet["petal_width"].text_color.set(interp_from=["red", "blue"])

    viewer.size = (100, 100)
    sheet.move_iloc(53, 4)
    sheet.move_iloc(49, 3)
    return viewer


@REG.register
def eval_example():
    viewer = TableViewer()
    sheet = viewer.add_spreadsheet(np.arange(100))
    sheet.cell[0, 2] = "0.20"
    sheet.cell.label[0, 2] = "freq:"
    sheet.cell[0, 1] = "&=np.sin(df.iloc[:, 0] * df.iloc[0, 2])"
    df = sheet.data
    sheet.plt.plot(df.iloc[:, 0], df.iloc[:, 1])
    viewer.size = (100, 100)
    sheet.move_iloc(3, 1)
    return viewer


@REG.register
def command_palette_example():
    viewer = TableViewer()
    viewer.add_spreadsheet()
    viewer.size = (100, 100)
    cmds.window.show_command_palette(viewer)
    return viewer


@REG.register
def custom_widget_example():
    viewer = TableViewer()
    sheet = viewer.add_spreadsheet()

    @magicgui
    def generate_random_data(shape=(100, 100), min="", max=""):
        pass

    @magicgui
    def read_csv(save_path: Path):
        pass

    sheet.add_side_widget(generate_random_data).show()
    sheet.add_side_widget(read_csv).show()

    sheet.add_overlay_widget(
        TextEdit(value="This widget is overlaid on the table."),
        label="Note",
        topleft=(2, 1),
        size=(2.5, 3.5),
    )

    viewer.size = (600, 450)
    return viewer


if __name__ == "__main__":
    REG.run_all()
