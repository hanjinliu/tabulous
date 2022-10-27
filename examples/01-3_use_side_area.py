from tabulous import TableViewer
from magicgui import magicgui

if __name__ == "__main__":
    viewer = TableViewer()
    sheet = viewer.add_spreadsheet(
        {
            "a": [1, 2, 3],
            "b": [4, 5, 6],
        }
    )

    @magicgui
    def update_cell(row: int, col: int, value: str):
        sheet.cell[row, col] = value

    sheet.add_side_widget(update_cell)

    viewer.show()
