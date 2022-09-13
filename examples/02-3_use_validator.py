from tabulous import TableViewer

# You can define validators for each column.
# A validator is called when a cell is edited, *after* the value is converted
# to the proper data type.

if __name__ == "__main__":
    viewer = TableViewer()
    size = 100
    table = viewer.add_table(
        {"name": ["A", "B", "C"], "value": [1, 2, 3]},
        editable=True,
    )

    @table.validator("value")
    def _value_validator(val: int):
        if val < 0:
            raise ValueError("Negative values are not allowed")

    viewer.show()
