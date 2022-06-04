from tabulous import TableViewer
from tabulous.types import TableData, TableColumn
from magicgui import magicgui
import numpy as np
import pandas as pd

@magicgui
def summarize_data(df: TableData) -> TableData:
    return df.agg([np.mean, np.std])

@magicgui
def extract_a_column(col: TableColumn) -> TableColumn:
    return col

if __name__ == "__main__":
    viewer = TableViewer()
    data = pd.DataFrame({
        "a": np.random.random(100), 
        "b": np.random.random(100) + 1,
        "c": np.random.random(100) * 2})
    viewer.add_table(data)
    viewer.add_dock_widget(summarize_data)
    viewer.add_dock_widget(extract_a_column)