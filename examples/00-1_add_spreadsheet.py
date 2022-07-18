from tabulous import TableViewer
from magicgui import magicgui
import numpy as np

if __name__ == "__main__":
    viewer = TableViewer()
    viewer.add_spreadsheet()  # add an empty spreadsheet
    viewer.add_spreadsheet(np.zeros((10, 10)))

    @magicgui
    def f():
        print(viewer.current_table.data)
        print(viewer.current_table.data.dtypes)

    f.show()
    viewer.show()
