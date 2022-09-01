from tabulous import TableViewer
import numpy as np
import pandas as pd
from magicgui import magicgui

# This example shows how to use the highlights.

if __name__ == "__main__":
    viewer = TableViewer()
    data = {
        "time": pd.Series([f"2022-01-0{x}" for x in range(1, 7)]),
        "value": np.random.random(6),
    }
    table = viewer.add_table(data)

    @table.add_side_widget
    @magicgui(auto_call=True)
    def set_highlight(row: int):
        if 0 <= row < len(table.index):
            table.highlights = [(row, slice(None))]

    viewer.show()
