from tabulous import TableViewer
import numpy as np
import pandas as pd

def loader():
    return np.random.random((10, 10))

if __name__ == "__main__":
    viewer = TableViewer()
    viewer.add_loader(loader)
    viewer.show()
