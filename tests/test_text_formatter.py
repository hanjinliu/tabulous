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

def test_spreadsheet_default_formatter():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"number": ["1.2", "1.23456789"]})
    assert _utils.get_cell_value(sheet.native, 0, 0) == "1.2"
    assert _utils.get_cell_value(sheet.native, 1, 0) == "1.23456789"
    sheet.dtypes.set_dtype("number", "float", formatting=False)
    assert _utils.get_cell_value(sheet.native, 0, 0) == "1.2"
    assert _utils.get_cell_value(sheet.native, 1, 0) == "1.23456789"
    sheet.dtypes.set_dtype("number", "float", formatting=True)
    assert _utils.get_cell_value(sheet.native, 0, 0) == "1.2000"
    assert _utils.get_cell_value(sheet.native, 1, 0) == "1.2346"
