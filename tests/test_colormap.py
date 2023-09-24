# import pandas as pd
# from tabulous.widgets import Table
# from tabulous.color import normalize_color
# import numpy as np

# cmap = {
#     "a": (255, 0, 0, 255),
#     "b": (0, 255, 0, 255),
#     "c": (0, 0, 255, 255),
# }

# def _cmap_func(x):
#     return cmap[x]

# def test_foreground():
#     table = Table({"char": ["a", "b", "c"]})
#     default_color = table.cell.text_color[0, 0]

#     table.text_color.set("char", cmap)
#     assert table.cell.text_color[0, 0] == normalize_color(cmap["a"])
#     assert table.cell.text_color[1, 0] == normalize_color(cmap["b"])
#     assert table.cell.text_color[2, 0] == normalize_color(cmap["c"])

#     table.text_color.set("char", None)
#     assert table.cell.text_color[0, 0] == default_color
#     assert table.cell.text_color[1, 0] == default_color
#     assert table.cell.text_color[2, 0] == default_color

#     table.text_color.set("char", _cmap_func)
#     assert table.cell.text_color[0, 0] == normalize_color(cmap["a"])
#     assert table.cell.text_color[1, 0] == normalize_color(cmap["b"])
#     assert table.cell.text_color[2, 0] == normalize_color(cmap["c"])


# def test_background():
#     table = Table({"char": ["a", "b", "c"]})
#     default_color = table.cell.background_color[0, 0]

#     table.background_color.set("char", cmap)
#     assert table.cell.background_color[0, 0] == normalize_color(cmap["a"])
#     assert table.cell.background_color[1, 0] == normalize_color(cmap["b"])
#     assert table.cell.background_color[2, 0] == normalize_color(cmap["c"])

#     table.background_color.set("char", None)
#     assert table.cell.background_color[0, 0] == default_color
#     assert table.cell.background_color[1, 0] == default_color
#     assert table.cell.background_color[2, 0] == default_color

#     table.background_color.set("char", _cmap_func)
#     assert table.cell.background_color[0, 0] == normalize_color(cmap["a"])
#     assert table.cell.background_color[1, 0] == normalize_color(cmap["b"])
#     assert table.cell.background_color[2, 0] == normalize_color(cmap["c"])


# def test_linear_interpolation():
#     table = Table(
#         {
#             "A": np.arange(10),
#             "B": np.arange(10) > 5,
#             "C": pd.date_range("2020-01-01", periods=10),
#         }
#     )
#     table.text_color.set("A", interp_from=["red", "blue"])
#     table.text_color.set("B", interp_from=["red", "blue"])
#     table.text_color.set("C", interp_from=["red", "blue"])
#     assert table.cell.text_color[0, 0] == normalize_color("red")
#     assert table.cell.text_color[4, 0] == normalize_color((141, 0, 113, 255))
#     assert table.cell.text_color[9, 0] == normalize_color("blue")
#     assert table.cell.text_color[0, 1] == normalize_color("red")
#     assert table.cell.text_color[9, 1] == normalize_color("blue")
#     assert table.cell.text_color[0, 2] == normalize_color("red")
#     assert table.cell.text_color[4, 2] == normalize_color((141, 0, 113, 255))
#     assert table.cell.text_color[9, 2] == normalize_color("blue")

# def test_linear_segmented():
#     table = Table(
#         {
#             "A": np.arange(-3, 4),
#             "C": pd.date_range("2020-01-01", periods=7),
#         }
#     )
#     table.text_color.set("A", interp_from=["red", "gray", "blue"])
#     table.text_color.set("C", interp_from=["red", "gray", "blue"])
#     assert table.cell.text_color[0, 0] == normalize_color("red")
#     assert table.cell.text_color[3, 0] == normalize_color("gray")
#     assert table.cell.text_color[6, 0] == normalize_color("blue")
#     assert table.cell.text_color[0, 1] == normalize_color("red")
#     assert table.cell.text_color[3, 1] == normalize_color("gray")
#     assert table.cell.text_color[6, 1] == normalize_color("blue")


# def test_invert():
#     table = Table({"A": np.arange(10)})
#     table.text_color.set("A", interp_from=["red", "blue"])
#     red = normalize_color("red")
#     red_inv = tuple(255 - x for x in red[:3]) + (red[3],)

#     assert table.cell.text_color[0, 0] == red
#     table.text_color.invert("A")
#     assert table.cell.text_color[0, 0] == red_inv

# def test_set_opacity():
#     table = Table({"A": np.arange(10)})
#     table.text_color.set("A", interp_from=["red", "blue"])
#     assert table.cell.text_color[0, 0][3] == 255

#     table.text_color.set_opacity("A", 0.5)
#     assert table.cell.text_color[0, 0][3] == 127

#     table.text_color.set("A", interp_from=["red", "blue"], opacity=0.5)
#     assert table.cell.text_color[0, 0][3] == 127

# def test_adjust_brightness():
#     table = Table({"A": np.arange(10)})
#     table.text_color.set("A", interp_from=["red", "blue"])
#     assert table.cell.text_color[0, 0] == normalize_color("red")
#     assert table.cell.text_color[9, 0] == normalize_color("blue")

#     table.text_color.adjust_brightness("A", 0.5)
#     assert table.cell.text_color[0, 0] > normalize_color("red")
#     assert table.cell.text_color[9, 0] > normalize_color("blue")

#     table.text_color.adjust_brightness("A", -0.5)
#     assert table.cell.text_color[0, 0] == normalize_color("red")
#     assert table.cell.text_color[9, 0] == normalize_color("blue")

#     table.text_color.adjust_brightness("A", -0.5)
#     assert table.cell.text_color[0, 0] < normalize_color("red")
#     assert table.cell.text_color[9, 0] < normalize_color("blue")

#     table.text_color.adjust_brightness("A", 0.5)
#     assert table.cell.text_color[0, 0] == normalize_color("red")
#     assert table.cell.text_color[9, 0] == normalize_color("blue")
