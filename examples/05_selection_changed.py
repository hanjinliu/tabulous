from tabulous import TableViewer
from tabulous.types import Selections
import numpy as np

if __name__ == "__main__":
    viewer = TableViewer()
    size = 100
    table = viewer.add_table(
        {
            "label": np.where(np.random.random(size) > 0.6, "A", "B"),
            "value-0": np.random.random(size),
            "value-1": np.random.normal(loc=2, scale=1, size=size),
        },
        editable=True,
    )

    @table.events.selections.connect
    def _on_selection_change(selection: Selections):
        strings = []
        for sel in selection:
            top_left, bottom_right = sel
            string = (
                f"data[{top_left.start}:{top_left.stop}, "
                f"{bottom_right.start}:{bottom_right.stop}]"
            )
            strings.append(string)
        print(", ".join(strings))

    viewer.show()
