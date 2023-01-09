from tabulous import TableViewer

def test_text_formatter():
    viewer = TableViewer(show=False)
    table = viewer.add_table({"number": [1, 2, 3], "char": ["a", "b", "c"]})
    assert table.cell.text[0, 0] == "1"

    # set formatter
    table.text_formatter("number", lambda x: str(x) + "!")
    assert table.cell.text[0, 0] == "1!"
    assert table.cell.text[0, 1] == "a"

    # reset formatter
    table.text_formatter("number", None)
    assert table.cell.text[0, 0] == "1"

def test_spreadsheet_default_formatter():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet({"number": ["1.2", "1.23456789"]})
    assert sheet.cell.text[0, 0] == "1.2"
    assert sheet.cell.text[1, 0] == "1.23456789"
    sheet.dtypes.set("number", "float", formatting=False)
    assert sheet.cell.text[0, 0] == "1.2"
    assert sheet.cell.text[1, 0] == "1.23456789"
    sheet.dtypes.set("number", "float", formatting=True)
    assert sheet.cell.text[0, 0] == "1.2000"
    assert sheet.cell.text[1, 0] == "1.2346"
