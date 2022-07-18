from tabulous import TableViewer
import numpy as np
import pandas as pd

if __name__ == "__main__":
    viewer = TableViewer()
    data = pd.DataFrame({"a": np.random.random(10), "b": np.random.random(10)})
    viewer.add_table(data)  # add DataFrame
    data = {"a": np.random.random(10), "b": np.random.random(10)}
    viewer.add_table(data)  # data that can be converted into a DataFrame
    viewer.tables[0].editable = True
    viewer.show()
