from magicgui.widgets import Container
from tabulous import MagicTableViewer
import pandas as pd

if __name__ == "__main__":
    viewer0 = MagicTableViewer(tab_position="top")
    viewer0.add_table(pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}))
    viewer1 = MagicTableViewer(tab_position="left")
    viewer1.add_table(
        pd.DataFrame(
            {"a": [1, 2, 3, 0],
            "categorical": pd.Series(["A", "B", "B", "A"], dtype="category"),
            "boolean": [True, False, True, False],
            }
        ),
        editable=True,
    )

    viewer1.add_spreadsheet(pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": ["A", "B", "A"]}))

    container = Container()
    container.append(viewer0)
    container.append(viewer1)
    container.show(True)
