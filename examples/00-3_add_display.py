from tabulous import TableViewer
import numpy as np

def loader():
    s = np.random.choice([3, 5, 7])
    return np.random.random((s, s))

if __name__ == "__main__":
    viewer = TableViewer()
    viewer.add_loader(loader)
    viewer.show()
