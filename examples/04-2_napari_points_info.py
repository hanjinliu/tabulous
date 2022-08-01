from tabulous import TableViewerWidget
import napari
import numpy as np
import pandas as pd

# This example shows how to use the TableViewerWidget to display all the coordinates of
# points in real time. When points are added, deleted or moved, table is also updated.

YX = ["y", "x"]

if __name__ == "__main__":
    viewer = napari.Viewer()
    npoints = 10
    points = np.random.normal(loc=[0, 0], scale=6, size=(npoints, 2))

    layer = viewer.add_points(points, size=2)

    table_viewer = TableViewerWidget()
    table = table_viewer.add_table(
        pd.DataFrame(layer.data, columns=YX), name=layer.name
    )

    @layer.events.set_data.connect
    def _on_data_changed(*_):
        df = pd.DataFrame(layer.data, columns=YX)
        table.data = df

    viewer.window.add_dock_widget(table_viewer)
    napari.run()
