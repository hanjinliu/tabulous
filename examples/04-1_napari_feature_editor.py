from tabulous import TableViewerWidget
import napari
import numpy as np
import pandas as pd

if __name__ == "__main__":
    viewer = napari.Viewer()
    npoints = 10
    points = np.random.normal(loc=[0, 0], scale=6, size=(npoints, 2))

    layer = viewer.add_points(
        points,
        features={
            "ID": np.arange(npoints),
            "feature": np.random.random(npoints),
            "label": pd.Series(np.random.choice(["A", "B", "C"], npoints), dtype="category"),
            "valid": np.random.choice([True, False], npoints),
        },
        size=2,
    )

    table_viewer = TableViewerWidget()
    table = table_viewer.add_table(layer.features, name=layer.name, editable=True)

    @table.events.data.connect
    @table.index.events.renamed.connect
    @table.columns.events.renamed.connect
    def _on_data_change(*args):
        # update features when any components of the data frame changed
        layer.features = table.data

    viewer.window.add_dock_widget(table_viewer)
    napari.run()
