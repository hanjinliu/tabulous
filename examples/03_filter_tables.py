from tabulous import TableViewer
import numpy as np

if __name__ == "__main__":
    viewer = TableViewer()
    size = 100
    table = viewer.add_table({
        "label": np.where(np.random.random(size) > 0.6, "A", "B"),
        "value-0": np.random.random(size),
        "value-1": np.random.normal(loc=2, scale=1, size=size),
    })
    table.filter = lambda df: df["label"] == "A"
