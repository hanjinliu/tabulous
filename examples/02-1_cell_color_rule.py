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

    @table.foreground_rule("label")
    def _set_color(val):
        if val == "A":
            return "green"
        else:
            return "red"

    @table.background_rule("value-0")
    def _set_color(val):
        alpha = int(255 * val)
        return [255, 255, 255, alpha]

    viewer.show()
