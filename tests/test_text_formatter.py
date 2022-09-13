from tabulous import TableViewer
from . import _utils

def test_text_formatter():
    viewer = TableViewer(show=False)
    table = viewer.add_table({"number": [1, 2, 3], "char": ["a", "b", "c"]})
    assert _utils.get_cell_value(table.native, 0, 0) == "1"

    # set formatter
    table.text_formatter("number", lambda x: str(x) + "!")
    assert _utils.get_cell_value(table.native, 0, 0) == "1!"
    assert _utils.get_cell_value(table.native, 0, 1) == "a"

    # reset formatter
    table.text_formatter("number", None)
    assert _utils.get_cell_value(table.native, 0, 0) == "1"
