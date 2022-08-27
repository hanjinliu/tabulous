import sys
import numpy as np
import tabulous as tbl

def colormap():
    viewer = tbl.TableViewer()
    table = viewer.open_sample("iris")
    lmin, lmax = table.data["sepal_length"].min(), table.data["sepal_length"].max()
    lrange = lmax - lmin
    @table.foreground_colormap("sepal_length")
    def _(x: float):
        red = np.array([255, 0, 0, 255], dtype=np.uint8)
        blue = np.array([0, 0, 255, 255], dtype=np.uint8)
        return (x - lmin) / lrange * blue + (lmax - x) / lrange * red

    @table.background_colormap("sepal_width")
    def _(x: float):
        return "green" if x < 3.2 else "violet"
    viewer.show()

def iris():
    viewer = tbl.TableViewer()
    viewer.open_sample("iris")
    viewer.show()

def table():
    df = {"label": ["A", "B", "C"],
          "value": [1.2, 2.4, 3.6],
          "valid": [True, False, True]}
    viewer = tbl.TableViewer()
    viewer.add_table(df, editable=True)
    viewer.show()

if __name__ == "__main__":
    arg = sys.argv[1]
    if arg == "colormap":
        colormap()
    elif arg == "iris":
        iris()
    elif arg == "table":
        table()
    else:
        raise ValueError(f"Unknown argument: {arg}")
