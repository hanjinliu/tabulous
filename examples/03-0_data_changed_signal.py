from tabulous import TableViewer
from tabulous.types import ItemInfo
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

    @table.events.data.connect
    def _on_data_change(info: ItemInfo):
        print(
            f"data[{info.row}, {info.column}] changed from "
            f"{info.old_value} to {info.value}."
        )

    def _on_data_change(info: ItemInfo):
        print("data at row 0 changed.")
    table.events.data[0, :].connect(_on_data_change)

    # NOTE: Python >= 3.9 supports this syntax
    # >>> @table.events.data[0, :].connect
    # >>> def _on_data_change(info: ItemInfo):
    # ...     print("data at row 0 changed.")

    viewer.show()
