from tabulous.widgets import Table

# def test_table_only_usage():
#     table = Table(df0)
#     assert table.data is df0
#     assert table.data.columns is df0.columns
#     assert table.data.index is df0.index
#     assert table.table_shape == df0.shape
#     assert get_cell_value(table._qwidget, 0, 0) == str(df0.iloc[0, 0])
#     edit_cell(table._qwidget, 0, 0, "11")
#     assert str(df0.iloc[0, 0]) == "11"
