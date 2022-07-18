from tabulous import TableViewer
import numpy as np
import pandas as pd

if __name__ == "__main__":
    viewer = TableViewer()
    data = pd.DataFrame(
        {"a": np.random.random(10),
         "b": np.random.random(10),
         "label": [0, 0, 0, 1, 1, 1, 1, 2, 2, 2],
         }
    )
    viewer.add_groupby(data.groupby("label"))
    viewer.show()
