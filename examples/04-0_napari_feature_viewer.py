from tabulous import MagicTableViewer
import napari
import numpy as np
from magicgui import magicgui

if __name__ == "__main__":
    viewer = napari.Viewer()
    points = np.random.normal(loc=[0, 0], scale=25, size=(100, 2))
    norms = np.sqrt(np.sum(points ** 2, axis=1))
    layer = viewer.add_points(
        points,
        features={
            "ID": np.arange(100),
            "norm": norms,
            "random numbers": np.full(100, np.nan),
        },
        size=2
    )

    table_viewer = MagicTableViewer()
    @table_viewer.add_loader
    def load_features():
        return layer.features

    @magicgui
    def f():
        features = layer.features
        features["random numbers"] = np.random.random(100)
        layer.features = features
        print(f"updated to: {layer.features}")

    viewer.window.add_dock_widget(table_viewer, name="Feature viewer")
    viewer.window.add_dock_widget(f)
    napari.run()
